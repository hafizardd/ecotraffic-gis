from collections.abc import Callable, Sequence
import logging
import os
from typing import Any

import cv2
import numpy as np

from cv.frame_sampler import FrameSampler

logger = logging.getLogger(__name__)

VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

DEFAULT_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "yolo", "yolov8l.pt")
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
            model_factory: Callable[[str], Any] = _load_yolo_model,
    ): 
        self.model_path = model_path
        self.confidence_threshold = float(confidence_threshold)
        normalized_device = "" if device is None else str(device).strip()
        self.device = (
            None if normalized_device.lower() in ("", "auto") else normalized_device
        )
        self.image_size = int(image_size)

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
        }
        if self.device is not None:
            options["device"] = self.device
        return options

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            raise ValueError("Input frame is empty or None")

    def _parse_result(
        self,
        frame: np.ndarray,
        result: Any,
        *,
        annotate: bool,
    ) -> tuple[dict[str, int], np.ndarray]:
        counts = {label: 0 for label in VEHICLE_CLASSES.values()}
        annotated_frame = frame.copy() if annotate else frame

        for box in result.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            if cls_id not in VEHICLE_CLASSES:
                continue
            if confidence < self.confidence_threshold:
                continue

            label = VEHICLE_CLASSES[cls_id]
            counts[label] += 1
            if annotate:
                self._draw_box(annotated_frame, box, label, confidence)
            logger.debug("Detected %s with confidence %.2f", label, confidence)

        return counts, annotated_frame
    
    def capture_frame(self, stream_url: str, referer: str = None) -> np.ndarray:
        """Compatibility wrapper; new processing code uses FrameSampler directly."""
        captured_frame = FrameSampler().capture(stream_url, referer)
        logger.info("Captured frame — shape: %s", captured_frame.frame.shape)
        return captured_frame.frame
 
    def _draw_box(
        self,
        frame: np.ndarray,
        box,
        label: str,
        conf: float,
    ) -> None:
        """Draw a bounding box + label onto the frame in-place."""
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        color = (0, 255, 0)
 
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            f"{label} {conf:.2f}",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
