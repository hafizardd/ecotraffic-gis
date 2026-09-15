"""Isolated tests: no model, database, or camera required."""
import os
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class CaptureTimeoutTests(unittest.TestCase):
    def test_timeouts_are_open_parameters_and_environment_is_restored(self):
        config = SimpleNamespace(settings=SimpleNamespace(
            FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS=10, FRAME_CAPTURE_READ_TIMEOUT_SECONDS=5))
        with patch.dict('sys.modules', {'app.core.config': config}):
            module = runpy.run_path(str(Path(__file__).parents[1] / 'cv/capture.py'))
        calls = []
        class Capture:
            def open(self, *args):
                calls.append((args, os.environ.get('OPENCV_FFMPEG_CAPTURE_OPTIONS')))
                return True
            def isOpened(self): return True
        cv = SimpleNamespace(VideoCapture=Capture, CAP_FFMPEG=1900,
                             CAP_PROP_OPEN_TIMEOUT_MSEC=53, CAP_PROP_READ_TIMEOUT_MSEC=54)
        with patch.dict(os.environ, {'OPENCV_FFMPEG_CAPTURE_OPTIONS': 'original'}):
            module['open_capture'](cv, 'https://camera.test/live', 'https://camera.test')
            self.assertEqual(os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'], 'original')
        self.assertEqual(calls[0][0], ('https://camera.test/live', 1900, [53, 10000, 54, 5000]))
        self.assertIn('Referer:', calls[0][1])

    def test_failed_open_releases_capture(self):
        config = SimpleNamespace(settings=SimpleNamespace(
            FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS=10, FRAME_CAPTURE_READ_TIMEOUT_SECONDS=5))
        with patch.dict('sys.modules', {'app.core.config': config}):
            module = runpy.run_path(str(Path(__file__).parents[1] / 'cv/capture.py'))
        released = []
        cap = SimpleNamespace(open=lambda *args: False, release=lambda: released.append(True))
        cv = SimpleNamespace(VideoCapture=lambda: cap, CAP_FFMPEG=1900,
                             CAP_PROP_OPEN_TIMEOUT_MSEC=53, CAP_PROP_READ_TIMEOUT_MSEC=54)
        self.assertIsNone(module['open_capture'](cv, 'camera', None))
        self.assertEqual(released, [True])

if __name__ == '__main__': unittest.main()
