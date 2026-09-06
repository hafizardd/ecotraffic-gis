from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading
import time

import numpy as np
import pytest

from app.services.detector_lifecycle import DetectorLifecycle
from cv.detector import VehicleDetector


class _Detector:
    def detect(self, frame):
        return frame


def test_lifecycle_constructs_one_detector_and_reuses_it():
    created = []

    def factory():
        detector = _Detector()
        created.append(detector)
        return detector

    lifecycle = DetectorLifecycle(factory)

    first = lifecycle.start()
    second = lifecycle.get()

    assert first is second
    assert created == [first]
    assert lifecycle.initialized is True


def test_lifecycle_is_safe_when_multiple_calls_start_together():
    created = []

    def factory():
        time.sleep(0.01)
        detector = _Detector()
        created.append(detector)
        return detector

    lifecycle = DetectorLifecycle(factory)
    with ThreadPoolExecutor(max_workers=8) as executor:
        detectors = list(executor.map(lambda _index: lifecycle.get(), range(16)))

    assert len(created) == 1
    assert all(detector is created[0] for detector in detectors)


def test_lifecycle_serializes_inference_with_one_process_model():
    state_lock = threading.Lock()
    active_calls = 0
    max_active_calls = 0

    class SlowDetector:
        def detect(self, frame):
            nonlocal active_calls, max_active_calls
            with state_lock:
                active_calls += 1
                max_active_calls = max(max_active_calls, active_calls)
            time.sleep(0.01)
            with state_lock:
                active_calls -= 1
            return frame

    lifecycle = DetectorLifecycle(SlowDetector)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lifecycle.detect, range(8)))

    assert results == list(range(8))
    assert max_active_calls == 1


def test_lifecycle_releases_reference_on_shutdown():
    created = []

    def factory():
        detector = _Detector()
        created.append(detector)
        return detector

    lifecycle = DetectorLifecycle(factory)
    first = lifecycle.start()

    lifecycle.stop()
    second = lifecycle.start()

    assert lifecycle.initialized is True
    assert first is not second
    assert len(created) == 2


def test_detector_passes_explicit_model_configuration():
    model_calls = []
    loaded_paths = []

    def model(frame, **options):
        model_calls.append((frame, options))
        return [SimpleNamespace(boxes=[])]

    detector = VehicleDetector(
        model_path="models/traffic.pt",
        confidence_threshold=0.4,
        device="cuda:0",
        image_size=512,
        model_factory=lambda path: loaded_paths.append(path) or model,
    )
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    counts, annotated = detector.detect(frame)

    assert loaded_paths == ["models/traffic.pt"]
    assert counts == {
        "car": 0,
        "motorcycle": 0,
        "bus": 0,
        "truck": 0,
    }
    assert annotated is not frame
    assert model_calls[0][0] is frame
    assert model_calls[0][1] == {
        "verbose": False,
        "conf": 0.4,
        "imgsz": 512,
        "device": "cuda:0",
    }


def test_detector_leaves_device_selection_automatic_by_default():
    options_seen = []

    def model(_frame, **options):
        options_seen.append(options)
        return [SimpleNamespace(boxes=[])]

    detector = VehicleDetector(model_factory=lambda _path: model, device="auto")
    detector.detect(np.zeros((2, 2, 3), dtype=np.uint8))

    assert "device" not in options_seen[0]


def test_detector_batches_frames_once_and_preserves_result_order():
    model_inputs = []

    def box(class_id):
        return SimpleNamespace(
            cls=np.array([class_id]),
            conf=np.array([0.9]),
        )

    def model(frames, **_options):
        model_inputs.append(frames)
        return [
            SimpleNamespace(boxes=[box(2)]),
            SimpleNamespace(boxes=[box(7), box(7)]),
        ]

    detector = VehicleDetector(model_factory=lambda _path: model)
    first_frame = np.zeros((2, 2, 3), dtype=np.uint8)
    second_frame = np.ones((2, 2, 3), dtype=np.uint8)

    results = detector.detect_batch(
        [first_frame, second_frame],
        annotate=False,
    )

    assert len(model_inputs) == 1
    assert model_inputs[0][0] is first_frame
    assert model_inputs[0][1] is second_frame
    assert results[0][0]["car"] == 1
    assert results[0][0]["truck"] == 0
    assert results[1][0]["car"] == 0
    assert results[1][0]["truck"] == 2
    assert results[0][1] is first_frame
    assert results[1][1] is second_frame


def test_detector_rejects_incomplete_batch_results():
    detector = VehicleDetector(model_factory=lambda _path: lambda *_args, **_kwargs: [])

    with pytest.raises(RuntimeError, match="0 results for 1 frames"):
        detector.detect_batch([np.zeros((2, 2, 3), dtype=np.uint8)])
