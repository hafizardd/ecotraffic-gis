from collections.abc import Callable, Mapping, Sequence
import logging
import os
from typing import Any

import cv2
import numpy as np

from cv.frame_sampler import FrameSampler
from cv.proposal_emission_factors import VEHICLE_CATEGORIES
from cv.rois import FILL, resolve, to_polygon_for_camera

logger = logging.getLogger(__name__)

TRAINED_VEHICLE_CLASSES = ("bus", "car", "motorcycle", "truck")

DEFAULT_YOLO_CATEGORY_MAPPING = {
    "motorcycle": "motorcycle",
    "car": "car",
    "bus": "bus",
    "truck": "truck",
}

DEFAULT_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "yolo", "yolo11n.pt")
)


def _load_yolo_model(model_path: str) -> Any:
    """Import the heavy runtime only in the process that owns the model."""
    from ultralytics import YOLO

    return YOLO(model_path)


class VehicleDetector:
    def __init__(
            self,
            model_path: str = DEFAULT_MODEL_PATH,
            confidence_threshold: float = 0.25,
            device: str | None = None,
            image_size: int = 640,
            category_mapping: Mapping[str, str] | None = None,
            model_factory: Callable[[str], Any] = _load_yolo_model,
            camera_id: str | None = None,
    ):
        self.model_path = model_path
        self.confidence_threshold = float(confidence_threshold)
        normalized_device = "" if device is None else str(device).strip()
        self.device = (
            None if normalized_device.lower() in ("", "auto") else normalized_device
        )
        self.image_size = int(image_size)
        self.category_mapping = dict(
            DEFAULT_YOLO_CATEGORY_MAPPING if category_mapping is None else category_mapping
        )
        self.camera_id = camera_id
        self._roi_key = resolve(camera_id)
        self._roi_cache: dict[tuple[int, int], Any] = {}

        logger.info(
            "yolo_model_loading",
            extra={
                "model_path": self.model_path,
                "device": self.device or "auto",
                "confidence_threshold": self.confidence_threshold,
                "image_size": self.image_size,
            },
        )
        self.model = model_factory(self.model_path)
        self.vehicle_classes = self._vehicle_classes_from_model()
        logger.info(
            "yolo_model_loaded",
            extra={"model_path": self.model_path, "device": self.device or "auto"},
        )
    
    def detect(self, frame: np.ndarray) -> tuple[dict[str, int], np.ndarray]:
        """
        Run vehicle detection on a single BGR frame (OpenCV format).
 
        Args:
            frame: np.ndarray — BGR image from cv2.imread or VideoCapture.
 
        Returns:
            counts: dict — {"car": int, "motorcycle": int, "bus": int, "truck": int}
            annotated_frame: np.ndarray — copy of frame with bounding boxes drawn.
 
        Raises:
            ValueError: if frame is None or empty.
        """
        self._validate_frame(frame)
        results = list(self.model(frame, **self._inference_options()))
        if len(results) != 1:
            raise RuntimeError(
                f"YOLO returned {len(results)} results for one input frame"
            )
        return self._parse_result(frame, results[0], annotate=True)

    def detect_batch(
        self,
        frames: Sequence[np.ndarray],
        *,
        annotate: bool = True,
    ) -> list[tuple[dict[str, int], np.ndarray]]:
        """Run one ordered YOLO call for multiple BGR frames."""
        batch = list(frames)
        if not batch:
            raise ValueError("Inference batch must contain at least one frame")
        for frame in batch:
            self._validate_frame(frame)

        results = list(self.model(batch, **self._inference_options()))
        if len(results) != len(batch):
            raise RuntimeError(
                f"YOLO returned {len(results)} results for {len(batch)} frames"
            )

        return [
            self._parse_result(frame, result, annotate=annotate)
            for frame, result in zip(batch, results)
        ]

    def _inference_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "verbose": False,
            "conf": self.confidence_threshold,
            "imgsz": self.image_size,
            "iou": 0.7,
            "max_det": 300,
            "agnostic_nms": False,
        }
        if self.device is not None:
            options["device"] = self.device
        return options

    def _vehicle_classes_from_model(self) -> dict[int, str]:
        names = getattr(self.model, "names", None)
        if isinstance(names, dict):
            names = [names[key] for key in sorted(names)]
        if isinstance(names, (list, tuple)):
            normalized = {
                index: str(name).strip().lower()
                for index, name in enumerate(names)
            }
            return {
                index: name
                for index, name in normalized.items()
                if name in self.category_mapping
            }
        return {
            index: name
            for index, name in enumerate(TRAINED_VEHICLE_CLASSES)
            if name in self.category_mapping
        }

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            raise ValueError("Input frame is empty or None")

    def _roi_polygon(self, frame: np.ndarray):
        if not self._roi_key:
            return None
        h, w = frame.shape[:2]
        key = (w, h)
        poly = self._roi_cache.get(key)
        if poly is None:
            import numpy as _np

            poly = _np.array(
                to_polygon_for_camera(w, h, self.camera_id), dtype=_np.int32
            )
            self._roi_cache[key] = poly
        return poly

    @staticmethod
    def _box_center_inside(poly, x1: int, y1: int, x2: int, y2: int) -> bool:
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        return bool(cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0)

    def _parse_result(
        self,
        frame: np.ndarray,
        result: Any,
        *,
        annotate: bool,
    ) -> tuple[dict[str, int], np.ndarray]:
        counts = {category: 0 for category in VEHICLE_CATEGORIES}
        annotated_frame = frame.copy() if annotate else frame
        roi_poly = self._roi_polygon(frame) if annotate else None
        if roi_poly is None and self._roi_key:
            # ROI counting still applies when annotate=False; resolve without copy.
            roi_poly = self._roi_polygon(frame)

        if annotate and roi_poly is not None:
            self._draw_roi(annotated_frame, roi_poly)

        for box in result.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            if cls_id not in self.vehicle_classes:
                continue
            if confidence < self.confidence_threshold:
                continue

            yolo_label = self.vehicle_classes[cls_id]
            category = self.category_mapping.get(yolo_label)
            if category is None:
                continue
            coords = self._box_xyxy(box)
            inside = (
                self._box_center_inside(roi_poly, *coords)
                if roi_poly is not None and coords is not None
                else True
            )
            if inside:
                counts[category] += 1
            if annotate and coords is not None:
                track_id = self._box_track_id(box)
                self._draw_box(
                    annotated_frame, box, category, confidence,
                    dimmed=not inside, track_id=track_id,
                )
            logger.debug("Detected %s with confidence %.2f", category, confidence)

        return counts, annotated_frame

    @staticmethod
    def _box_xyxy(box) -> tuple[int, int, int, int] | None:
        try:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
        except (AttributeError, TypeError, IndexError, ValueError):
            return None
        return (x1, y1, x2, y2)

    @staticmethod
    def _box_track_id(box) -> int | None:
        track = getattr(box, "id", None)
        if track is None:
            return None
        try:
            return int(track[0])
        except (TypeError, IndexError, ValueError):
            return None
    
    def capture_frame(self, stream_url: str, referer: str = None) -> np.ndarray:
        """Compatibility wrapper; new processing code uses FrameSampler directly."""
        captured_frame = FrameSampler().capture(stream_url, referer)
        logger.info("Captured frame — shape: %s", captured_frame.frame.shape)
        return captured_frame.frame
 
    def _draw_roi(self, frame: np.ndarray, roi_poly) -> None:
        """Fill ROI polygon with FILL alpha + green border, in-place."""
        overlay = frame.copy()
        cv2.fillPoly(overlay, [roi_poly], (0, 255, 0))
        alpha = FILL[3] / 255.0
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.polylines(frame, [roi_poly], True, (0, 255, 0), 2)

    def _draw_box(
        self,
        frame: np.ndarray,
        box,
        label: str,
        conf: float,
        *,
        dimmed: bool = False,
        track_id: int | None = None,
    ) -> None:
        """Draw a bounding box + label onto the frame in-place."""
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        color = (0, 255, 0) if not dimmed else (128, 128, 128)
        text = f"{label} {conf:.2f}"
        if track_id is not None:
            text = f"#{track_id} {text}"

        if dimmed:
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            text,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
