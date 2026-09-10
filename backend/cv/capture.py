"""Shared single-frame HLS capture with Referer + timeouts.

Wowza-backed Jogja CCTV streams reject requests without a Referer and hang
without explicit FFmpeg timeouts. Both the tracking worker and the historical
snapshot worker open captures this way; keep the behavior here only.
"""

from __future__ import annotations

import os

from app.core.config import settings


def open_capture(cv2_module, stream_url: str, referer: str | None):
    """Open a capture with Referer + timeouts, or return None on failure."""
    env_key = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    previous = os.environ.get(env_key)
    try:
        if referer:
            os.environ[env_key] = f"headers=Referer: {referer}\r\n"
        cap = cv2_module.VideoCapture()
        open_ms = int(float(settings.FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS) * 1000)
        read_ms = int(float(settings.FRAME_CAPTURE_READ_TIMEOUT_SECONDS) * 1000)
        for prop, value in (
            ("CAP_PROP_OPEN_TIMEOUT_MSEC", open_ms),
            ("CAP_PROP_READ_TIMEOUT_MSEC", read_ms),
        ):
            prop_id = getattr(cv2_module, prop, None)
            if prop_id is not None:
                try:
                    cap.set(prop_id, value)
                except Exception:
                    pass
        backend = getattr(cv2_module, "CAP_FFMPEG", 0)
        buffer_prop = getattr(cv2_module, "CAP_PROP_BUFFERSIZE", None)
        if buffer_prop is not None:
            try:
                cap.set(buffer_prop, 1)
            except Exception:
                pass
        if not cap.open(stream_url, backend) or not cap.isOpened():
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
