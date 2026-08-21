import cv2
import os

from ultralytics import YOLO
import numpy as np
import logging

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

class VehicleDetector:
    def __init__(
            self,
            model_path: str = DEFAULT_MODEL_PATH,
            confidence_threshold: float = 0.25
    ): 
        self.model_path = model_path
        self.confidence_threshold = float(confidence_threshold)

        logger.info(f"Loading YOLO model from {self.model_path}")
        self.model = YOLO(self.model_path)
        logger.info("Model loaded successfully")
    
    def detect(self, frame:np.ndarray) -> tuple[dict, np.ndarray]:
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
        if frame is None or frame.size == 0:
            raise ValueError("Input frame is empty or None")
            
        counts = {label: 0 for label in VEHICLE_CLASSES.values()}
        annotated_frame = frame.copy()

        results = self.model(frame, verbose=False, conf=self.confidence_threshold)

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])

                if cls_id not in VEHICLE_CLASSES:
                    continue

                if conf < self.confidence_threshold:
                    continue

                label = VEHICLE_CLASSES[cls_id]
                counts[label] += 1

                self._draw_box(annotated_frame, box, label, conf)
                logger.debug(f"Detected {label} with confidence {conf:.2f}")

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
