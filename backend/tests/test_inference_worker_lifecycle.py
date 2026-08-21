from datetime import datetime, timezone
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


def test_worker_aggregation_uses_capture_metadata_and_configured_window(monkeypatch):
    observations = []
    expected = object()
    monkeypatch.setattr(
        inference_worker.emission_aggregator,
        "add",
        lambda observation: observations.append(observation) or expected,
    )
    captured_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    job = SimpleNamespace(
        camera_id="camera-12",
        camera_database_id="database-camera-12",
        job_id="job-12",
        captured_at=captured_at,
        frame_acquisition_latency_s=1.5,
    )

    result = inference_worker._aggregate_observation(
        job,
        {"car": 2, "motorcycle": 3, "bus": 1, "truck": 0},
        queue_wait_s=2.5,
        inference_latency_s=3.5,
        cycle_duration_s=5,
    )

    assert result is expected
    assert observations[0].camera_id == "camera-12"
    assert observations[0].captured_at == captured_at
    assert observations[0].vehicle_counts["motorcycle"] == 3
    assert observations[0].queue_wait_s == 2.5
    assert (
        inference_worker.emission_aggregator.window_seconds
        == inference_worker.settings.EMISSION_AGGREGATION_WINDOW_SECONDS
    )


def test_aggregation_failure_is_isolated_from_raw_result_processing(monkeypatch):
    monkeypatch.setattr(
        inference_worker,
        "_aggregate_observation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("failed")),
    )
    job = SimpleNamespace(camera_id="camera-12", job_id="job-12")

    metadata = inference_worker._record_aggregation(
        job,
        {"car": 1, "motorcycle": 0, "bus": 0, "truck": 0},
        queue_wait_s=1,
        inference_latency_s=2,
        cycle_duration_s=3,
    )

    assert metadata == {
        "aggregation_status": "failed",
        "aggregation_window_seconds": (
            inference_worker.settings.EMISSION_AGGREGATION_WINDOW_SECONDS
        ),
    }
