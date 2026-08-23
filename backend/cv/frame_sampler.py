from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import subprocess
import time
from typing import Any, Callable


logger = logging.getLogger(__name__)


class FrameCaptureError(RuntimeError):
    """Raised when neither supported capture mechanism returns a frame."""


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    frame: Any
    captured_at: datetime
    acquisition_latency_s: float
    method: str


class FrameSampler:
    """Acquire one frame without retaining a long-lived stream connection."""

    def __init__(
        self,
        *,
        open_timeout_seconds: int = 10,
        read_timeout_seconds: int = 10,
        ffmpeg_timeout_seconds: int = 30,
        cv2_module: Any | None = None,
        run: Callable[..., Any] = subprocess.run,
        decode_image: Callable[[bytes], Any] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] | None = None,
    ):
        for timeout in (
            open_timeout_seconds,
            read_timeout_seconds,
            ffmpeg_timeout_seconds,
        ):
            if timeout <= 0:
                raise ValueError("Frame capture timeouts must be positive")

        self.open_timeout_seconds = open_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.ffmpeg_timeout_seconds = ffmpeg_timeout_seconds
        self._cv2_module = cv2_module
        self._run = run
        self._decode_image = decode_image or self._decode_with_opencv
        self._monotonic = monotonic
        self._now = now or (lambda: datetime.now(timezone.utc))

    def capture(self, stream_url: str, referer: str | None = None) -> CapturedFrame:
        """Capture a single frame, first via OpenCV and then via FFmpeg."""

        started_at = self._monotonic()
        frame = self._capture_opencv(stream_url)
        if self._is_valid_frame(frame):
            return self._build_captured_frame(frame, "opencv", started_at)

        logger.warning("opencv_frame_capture_failed; trying ffmpeg fallback")
        frame = self._capture_ffmpeg(stream_url, referer)
        if self._is_valid_frame(frame):
            return self._build_captured_frame(frame, "ffmpeg", started_at)

        raise FrameCaptureError("No frame could be captured from the configured stream")

    def _build_captured_frame(
        self,
        frame: Any,
        method: str,
        started_at: float,
    ) -> CapturedFrame:
        return CapturedFrame(
            frame=frame,
            captured_at=self._now(),
            acquisition_latency_s=self._monotonic() - started_at,
            method=method,
        )

    def _capture_opencv(self, stream_url: str) -> Any | None:
        cv2 = self._get_cv2()
        if cv2 is None:
            return None

        capture = None
        try:
            capture = cv2.VideoCapture()
            self._set_capture_timeout(
                capture,
                getattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", None),
                self.open_timeout_seconds,
            )
            self._set_capture_timeout(
                capture,
                getattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC", None),
                self.read_timeout_seconds,
            )
            backend = getattr(cv2, "CAP_FFMPEG", 0)
            if not capture.open(stream_url, backend) or not capture.isOpened():
                return None

            ok, frame = capture.read()
            return frame if ok else None
        except Exception:
            logger.warning("opencv_frame_capture_error", exc_info=True)
            return None
        finally:
            if capture is not None:
                capture.release()

    @staticmethod
    def _set_capture_timeout(capture: Any, property_id: int | None, seconds: int) -> None:
        if property_id is not None:
            capture.set(property_id, seconds * 1000)

    def _capture_ffmpeg(self, stream_url: str, referer: str | None) -> Any | None:
        command = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-rw_timeout",
            str(self.ffmpeg_timeout_seconds * 1_000_000),
        ]
        if referer:
            command.extend(["-headers", f"Referer: {referer}\r\n"])
        command.extend(
            [
                "-i",
                stream_url,
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ]
        )

        try:
            completed = self._run(
                command,
                capture_output=True,
                timeout=self.ffmpeg_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg_frame_capture_timed_out")
            return None
        except Exception:
            logger.warning("ffmpeg_frame_capture_error", exc_info=True)
            return None

        if completed.returncode != 0 or not completed.stdout:
            logger.warning(
                "ffmpeg_frame_capture_failed",
                extra={"returncode": completed.returncode},
            )
            return None

        try:
            return self._decode_image(completed.stdout)
        except Exception:
            logger.warning("ffmpeg_frame_decode_error", exc_info=True)
            return None

    def _get_cv2(self) -> Any | None:
        if self._cv2_module is not None:
            return self._cv2_module

        try:
            import cv2
        except ImportError:
            logger.warning("opencv_not_available_for_frame_capture")
            return None

        self._cv2_module = cv2
        return cv2

    @staticmethod
    def _decode_with_opencv(image_bytes: bytes) -> Any:
        import cv2
        import numpy as np

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    @staticmethod
    def _is_valid_frame(frame: Any) -> bool:
        return frame is not None and getattr(frame, "size", 1) != 0
