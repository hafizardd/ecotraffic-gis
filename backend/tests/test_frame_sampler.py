from datetime import datetime, timezone
import subprocess
from types import SimpleNamespace

import pytest

from cv.frame_sampler import FrameCaptureError, FrameSampler


class _Frame:
    size = 1


class _Capture:
    def __init__(self, *, opens: bool, frame=None):
        self.opens = opens
        self.frame = frame
        self.released = False
        self.properties = []
        self.open_arguments = None

    def set(self, property_id, value):
        self.properties.append((property_id, value))

    def open(self, *arguments):
        self.open_arguments = arguments
        return self.opens

    def isOpened(self):
        return self.opens

    def read(self):
        return self.frame is not None, self.frame

    def release(self):
        self.released = True


class _Cv2:
    CAP_PROP_OPEN_TIMEOUT_MSEC = 1
    CAP_PROP_READ_TIMEOUT_MSEC = 2
    CAP_FFMPEG = 3

    def __init__(self, capture):
        self.capture = capture

    def VideoCapture(self):
        return self.capture


def _sampler(*, capture, run, decode_image=lambda _bytes: _Frame()):
    clock_values = iter([10.0, 12.5])
    return FrameSampler(
        open_timeout_seconds=4,
        read_timeout_seconds=5,
        ffmpeg_timeout_seconds=6,
        cv2_module=_Cv2(capture),
        run=run,
        decode_image=decode_image,
        monotonic=lambda: next(clock_values),
        now=lambda: datetime(2026, 8, 21, tzinfo=timezone.utc),
    )


def test_opencv_capture_returns_metadata_and_releases_resource():
    frame = _Frame()
    capture = _Capture(opens=True, frame=frame)
    sampler = _sampler(capture=capture, run=lambda **_kwargs: None)

    captured = sampler.capture("https://example.test/stream.m3u8")

    assert captured.frame is frame
    assert captured.method == "opencv"
    assert captured.acquisition_latency_s == 2.5
    assert captured.captured_at == datetime(2026, 8, 21, tzinfo=timezone.utc)
    assert capture.released is True
    assert capture.properties == [(1, 4000), (2, 5000)]


def test_ffmpeg_fallback_releases_opencv_and_decodes_frame():
    capture = _Capture(opens=False)
    completed = SimpleNamespace(returncode=0, stdout=b"encoded-frame")
    calls = []
    sampler = _sampler(
        capture=capture,
        run=lambda command, **kwargs: calls.append((command, kwargs)) or completed,
    )

    captured = sampler.capture(
        "https://example.test/stream.m3u8",
        "https://example.test/",
    )

    assert captured.method == "ffmpeg"
    assert capture.released is True
    assert calls[0][1]["timeout"] == 6
    assert "-rw_timeout" in calls[0][0]
    assert ["-headers", "Referer: https://example.test/\r\n"] == calls[0][0][
        calls[0][0].index("-headers") : calls[0][0].index("-headers") + 2
    ]


def test_capture_raises_when_all_capture_methods_fail():
    capture = _Capture(opens=False)
    sampler = _sampler(
        capture=capture,
        run=lambda _command, **_kwargs: SimpleNamespace(returncode=1, stdout=b""),
    )

    with pytest.raises(FrameCaptureError):
        sampler.capture("https://example.test/stream.m3u8")

    assert capture.released is True


def test_ffmpeg_timeout_is_isolated_as_capture_failure():
    capture = _Capture(opens=False)
    sampler = _sampler(
        capture=capture,
        run=lambda _command, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("ffmpeg", 6)
        ),
    )

    with pytest.raises(FrameCaptureError):
        sampler.capture("https://example.test/stream.m3u8")
