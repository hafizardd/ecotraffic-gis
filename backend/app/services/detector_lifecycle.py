from collections.abc import Callable
import threading
from typing import Generic, Protocol, TypeVar


class Detector(Protocol):
    def detect(self, frame): ...

    def detect_batch(self, frames, **kwargs): ...


DetectorType = TypeVar("DetectorType", bound=Detector)


class DetectorLifecycle(Generic[DetectorType]):
    """Own exactly one reusable detector inside the current worker process."""

    def __init__(self, factory: Callable[[], DetectorType]):
        self._factory = factory
        self._detector: DetectorType | None = None
        self._lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def initialized(self) -> bool:
        return self._detector is not None

    def start(self) -> DetectorType:
        detector = self._detector
        if detector is not None:
            return detector

        with self._lock:
            if self._detector is None:
                self._detector = self._factory()
            return self._detector

    def get(self) -> DetectorType:
        """Return the persistent detector, lazily starting non-solo workers."""
        return self.start()

    def detect(self, frame):
        """Serialize access so one process never drives its model concurrently."""
        with self._inference_lock:
            return self.get().detect(frame)

    def detect_batch(self, frames, **kwargs):
        """Run one ordered batch against the process-owned model."""
        with self._inference_lock:
            return self.get().detect_batch(frames, **kwargs)

    def stop(self) -> None:
        with self._lock:
            self._detector = None
