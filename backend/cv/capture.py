"""Shared single-frame HLS capture with Referer + timeouts.

Wowza-backed Jogja CCTV streams reject requests without a Referer and hang
without explicit FFmpeg timeouts. Both the tracking worker and the historical
snapshot worker open captures this way; keep the behavior here only.
"""

from __future__ import annotations

import os
import threading

from app.core.config import settings


_capture_open_lock = threading.Lock()

def open_capture(cv2_module, stream_url: str, referer: str | None):
    """Open a capture with Referer + timeouts, or return None on failure."""
    # FFmpeg options are process-global; prevent camera Referer races.
    with _capture_open_lock:
        return _open_capture_locked(cv2_module, stream_url, referer)


def _open_capture_locked(cv2_module, stream_url: str, referer: str | None):
    env_key = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    previous = os.environ.get(env_key)
    try:
        if not referer:
            os.environ.pop(env_key, None)
        if referer:
            os.environ[env_key] = f"headers=Referer: {referer}\r\n"
        cap = cv2_module.VideoCapture()
        open_ms = int(float(settings.FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS) * 1000)
        read_ms = int(float(settings.FRAME_CAPTURE_READ_TIMEOUT_SECONDS) * 1000)
        # These FFmpeg properties are open-only; cap.set silently ignores them.
        params = [
            cv2_module.CAP_PROP_OPEN_TIMEOUT_MSEC, open_ms,
            cv2_module.CAP_PROP_READ_TIMEOUT_MSEC, read_ms,
        ]
        backend = cv2_module.CAP_FFMPEG
        if not cap.open(stream_url, backend, params) or not cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
            return None
        return cap
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous


def grab_frame(stream_url: str, referer: str | None):
    """Open the stream, grab the newest available BGR frame, release."""
    import cv2

    cap = open_capture(cv2, stream_url, referer)
    if cap is None:
        return None
    try:
        ok = cap.grab()
        if ok:
            ok, frame = cap.retrieve()
        else:
            frame = None
        return frame if ok and frame is not None else None
    finally:
        try:
            cap.release()
        except Exception:
            pass
