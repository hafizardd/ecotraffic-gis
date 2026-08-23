from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from app.services.inference_queue import ReservationStatus
from app.services.camera_health import CameraFailureUpdate, CameraHealthStatus
from cv.frame_sampler import FrameCaptureError
from cv.frame_sampler import CapturedFrame
from cv.frame_store import StoredFrame
from app.workers import sampling_worker


class _Task:
    def retry(self, *, exc, countdown):
        raise AssertionError(f"unexpected retry: {exc} after {countdown}s")


class _Queue:
    def __init__(self, status=ReservationStatus.ACCEPTED):
        self.status = status
        self.released = []

    def reserve(self, _camera_id, _job_id):
        return self.status

    def release(self, camera_id, job_id):
        self.released.append((camera_id, job_id))

    def depth(self):
        return 1


def _camera():
    return SimpleNamespace(
        id=uuid.UUID("2b0ea8e6-a790-44a5-aa76-8b40787c0f02"),
        camera_id="camera-12",
        stream_url="https://example.test/stream.m3u8",
        referer="https://example.test/",
        priority="high",
        sampling_interval_seconds=10,
    )


def test_sampling_enqueues_metadata_without_frame_bytes(monkeypatch):
    captured = CapturedFrame(
        frame=object(),
        captured_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
        acquisition_latency_s=1.25,
        method="opencv",
    )
    sent = []
    queue = _Queue()
    monkeypatch.setattr(sampling_worker, "get_active_camera_source", lambda _id: _camera())
    monkeypatch.setattr(sampling_worker, "inference_queue", queue)
    monkeypatch.setattr(
        sampling_worker.camera_health_service,
        "record_capture_success",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        sampling_worker.frame_sampler,
        "capture",
        lambda _url, _referer: captured,
    )
    monkeypatch.setattr(
        sampling_worker.frame_store,
        "store",
        lambda job_id, _frame: StoredFrame(
            key=f"inference:frame:{job_id}",
            size_bytes=1234,
        ),
    )
    monkeypatch.setattr(
        sampling_worker.celery_app,
        "send_task",
        lambda *args, **kwargs: sent.append((args, kwargs)),
    )

    result = sampling_worker._sample_and_enqueue(_Task(), "camera-12")

    assert result["status"] == "queued"
    assert sent[0][0] == (sampling_worker.INFERENCE_TASK,)
    assert sent[0][1]["queue"] == "inference"
    payload = sent[0][1]["kwargs"]["job_payload"]
    assert payload["camera_id"] == "camera-12"
    assert payload["frame_size_bytes"] == 1234
    assert payload["frame_key"].startswith("inference:frame:")
    assert all(not isinstance(value, bytes) for value in payload.values())


def test_capture_failure_records_backoff_without_task_retry(monkeypatch):
    queue = _Queue()
    updates = []
    monkeypatch.setattr(sampling_worker, "get_active_camera_source", lambda _id: _camera())
    monkeypatch.setattr(sampling_worker, "inference_queue", queue)
    monkeypatch.setattr(
        sampling_worker.frame_sampler,
        "capture",
        lambda *_args: (_ for _ in ()).throw(FrameCaptureError("stream unavailable")),
    )
    monkeypatch.setattr(
        sampling_worker.camera_health_service,
        "record_capture_failure",
        lambda *_args: updates.append(True)
        or CameraFailureUpdate(
            failure_count=2,
            status=CameraHealthStatus.DEGRADED,
            retry_delay_seconds=10,
            next_sample_at=datetime(2026, 8, 21, 0, 0, 10, tzinfo=timezone.utc),
        ),
    )

    result = sampling_worker._sample_and_enqueue(_Task(), "camera-12")

    assert updates == [True]
    assert result["status"] == "capture_failed"
    assert result["failure_count"] == 2
    assert result["retry_delay_seconds"] == 10
    assert len(queue.released) == 1


def test_full_queue_skips_capture_explicitly(monkeypatch):
    queue = _Queue(status=ReservationStatus.FULL)
    monkeypatch.setattr(sampling_worker, "get_active_camera_source", lambda _id: _camera())
    monkeypatch.setattr(sampling_worker, "inference_queue", queue)
    monkeypatch.setattr(
        sampling_worker.frame_sampler,
        "capture",
        lambda *_args: (_ for _ in ()).throw(AssertionError("capture should not run")),
    )

    result = sampling_worker._sample_and_enqueue(_Task(), "camera-12")

    assert result["status"] == "full"
    assert result["queue_depth"] == 1


def test_sampling_and_legacy_tasks_register_on_the_sampling_worker():
    sampling_worker.celery_app.loader.import_default_modules()

    assert sampling_worker.SAMPLE_CAMERA_TASK in sampling_worker.celery_app.tasks
    assert sampling_worker.LEGACY_PROCESS_CAMERA_TASK in sampling_worker.celery_app.tasks
    assert (
        sampling_worker.celery_app.conf.task_routes[sampling_worker.INFERENCE_TASK][
            "queue"
        ]
        == "inference"
    )
