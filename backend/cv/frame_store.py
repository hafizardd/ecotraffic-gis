from dataclasses import dataclass
from typing import Any


class FrameEncodingError(RuntimeError):
    pass


class FramePayloadTooLarge(FrameEncodingError):
    pass


class FrameUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoredFrame:
    key: str
    size_bytes: int


class RedisFrameStore:
    """Short-lived compressed frame storage outside the Celery message body."""

    def __init__(
        self,
        redis_client: Any,
        *,
        ttl_seconds: int,
        max_bytes: int,
        jpeg_quality: int,
        cv2_module: Any | None = None,
        numpy_module: Any | None = None,
        key_prefix: str = "inference:frame:",
    ):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.max_bytes = max_bytes
        self.jpeg_quality = jpeg_quality
        self._cv2_module = cv2_module
        self._numpy_module = numpy_module
        self.key_prefix = key_prefix

    def store(self, job_id: str, frame: Any) -> StoredFrame:
        cv2 = self._get_cv2()
        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
        )
        if not ok:
            raise FrameEncodingError("OpenCV could not encode the sampled frame")

        payload = encoded.tobytes()
        size_bytes = len(payload)
        if size_bytes > self.max_bytes:
            raise FramePayloadTooLarge(
                f"Encoded frame is {size_bytes} bytes; limit is {self.max_bytes} bytes"
            )

        key = f"{self.key_prefix}{job_id}"
        self.redis.setex(key, self.ttl_seconds, payload)
        return StoredFrame(key=key, size_bytes=size_bytes)

    def load(self, key: str) -> Any:
        payload = self.redis.get(key)
        if payload is None:
            raise FrameUnavailable("Inference frame expired or is unavailable")

        cv2 = self._get_cv2()
        np = self._get_numpy()
        encoded = np.frombuffer(payload, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None or getattr(frame, "size", 0) == 0:
            raise FrameEncodingError("Stored inference frame could not be decoded")
        return frame

    def delete(self, key: str) -> None:
        self.redis.delete(key)

    def _get_cv2(self) -> Any:
        if self._cv2_module is None:
            import cv2

            self._cv2_module = cv2
        return self._cv2_module

    def _get_numpy(self) -> Any:
        if self._numpy_module is None:
            import numpy as np

            self._numpy_module = np
        return self._numpy_module
