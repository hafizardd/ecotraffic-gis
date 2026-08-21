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


def test_worker_startup_eagerly_initializes_in_process_pools(monkeypatch):
    starts = []
    batcher_starts = []
    monkeypatch.setattr(
        inference_worker.detector_lifecycle,
        "start",
        lambda: starts.append("started"),
    )
    monkeypatch.setattr(
        inference_worker.inference_batcher,
        "start",
        lambda: batcher_starts.append("started"),
    )
    solo_pool = type("TaskPool", (), {})
    solo_pool.__module__ = "celery.concurrency.solo"

    inference_worker.initialize_inference_worker_detector(
        sender=SimpleNamespace(pool_cls=solo_pool)
    )
    inference_worker.initialize_inference_worker_detector(
        sender=SimpleNamespace(pool_cls="threads")
    )
    inference_worker.initialize_inference_worker_detector(
        sender=SimpleNamespace(pool_cls="prefork")
    )

    assert starts == ["started", "started"]
    assert batcher_starts == ["started", "started"]


def test_worker_shutdown_releases_detector(monkeypatch):
    stops = []
    batcher_stops = []
    monkeypatch.setattr(
        inference_worker.detector_lifecycle,
        "stop",
        lambda: stops.append("stopped"),
    )
    monkeypatch.setattr(
        inference_worker.inference_batcher,
        "stop",
        lambda: batcher_stops.append("stopped"),
    )

    inference_worker.shutdown_inference_worker_detector()

    assert stops == ["stopped"]
    assert batcher_stops == ["stopped"]


def test_worker_batcher_uses_configured_limits():
    assert (
        inference_worker.inference_batcher.max_batch_size
        == inference_worker.settings.INFERENCE_MAX_BATCH_SIZE
    )
    assert inference_worker.inference_batcher.max_wait_s == (
        inference_worker.settings.INFERENCE_MAX_BATCH_WAIT_MS / 1000
    )
    assert inference_worker.settings.INFERENCE_BATCH_RESULT_TIMEOUT_SECONDS > 0
    assert (
        inference_worker.celery_app.conf.worker_concurrency
        == inference_worker.settings.INFERENCE_WORKER_CONCURRENCY
    )
