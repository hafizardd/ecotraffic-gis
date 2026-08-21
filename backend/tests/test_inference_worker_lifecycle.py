from types import SimpleNamespace

from app.workers import inference_worker


def test_detector_factory_uses_inference_settings(monkeypatch):
    received = []
    expected = object()
    monkeypatch.setattr(
        inference_worker,
        "VehicleDetector",
        lambda **kwargs: received.append(kwargs) or expected,
    )
    monkeypatch.setattr(inference_worker.settings, "YOLO_MODEL_PATH", "model.pt")
    monkeypatch.setattr(inference_worker.settings, "YOLO_DEVICE", "cpu")
    monkeypatch.setattr(inference_worker.settings, "YOLO_IMAGE_SIZE", 320)
    monkeypatch.setattr(inference_worker.settings, "CONFIDENCE_THRESHOLD", 0.3)

    detector = inference_worker._build_detector()

    assert detector is expected
    assert received == [
        {
            "model_path": "model.pt",
            "confidence_threshold": 0.3,
            "device": "cpu",
            "image_size": 320,
        }
    ]


def test_worker_startup_eagerly_initializes_only_the_solo_pool(monkeypatch):
    starts = []
    monkeypatch.setattr(
        inference_worker.detector_lifecycle,
        "start",
        lambda: starts.append("started"),
    )
    solo_pool = type("TaskPool", (), {})
    solo_pool.__module__ = "celery.concurrency.solo"

    inference_worker.initialize_inference_worker_detector(
        sender=SimpleNamespace(pool_cls=solo_pool)
    )
    inference_worker.initialize_inference_worker_detector(
        sender=SimpleNamespace(pool_cls="prefork")
    )

    assert starts == ["started"]


def test_worker_shutdown_releases_detector(monkeypatch):
    stops = []
    monkeypatch.setattr(
        inference_worker.detector_lifecycle,
        "stop",
        lambda: stops.append("stopped"),
    )

    inference_worker.shutdown_inference_worker_detector()

    assert stops == ["stopped"]
