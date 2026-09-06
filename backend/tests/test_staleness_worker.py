from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.camera_health import CameraHealthPolicy, CameraHealthService
from app.workers import staleness_worker


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


class _Result:
    def __init__(self, cameras):
        self._cameras = cameras

    def scalars(self):
        return self

    def all(self):
        return self._cameras


class _Session:
    def __init__(self, cameras):
        self._cameras = cameras

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _query):
        return _Result(self._cameras)


def test_staleness_sweep_degrades_and_marks_offline(monkeypatch):
    fresh = SimpleNamespace(
        camera_id="camera-fresh", data_source="LIVE", status="active",
        last_success_at=NOW - timedelta(seconds=10),
    )
    stale = SimpleNamespace(
        camera_id="camera-stale", data_source="LIVE", status="active",
        last_success_at=NOW - timedelta(seconds=200),
    )
    dead_stream = SimpleNamespace(
        camera_id="camera-dead", data_source="HISTORICAL", status="active",
        last_success_at=None,
    )
    monkeypatch.setattr(staleness_worker, "get_sync_db", lambda: _Session([fresh, stale, dead_stream]))
    monkeypatch.setattr(
        staleness_worker,
        "camera_health_service",
        CameraHealthService(CameraHealthPolicy(
            retry_base_seconds=5, retry_max_seconds=60, failures_before_offline=4,
            stale_threshold_seconds=90, offline_threshold_seconds=300,
        )),
    )
    monkeypatch.setattr(staleness_worker, "datetime", SimpleNamespace(now=lambda _tz: NOW))

    result = staleness_worker.check_camera_staleness()

    assert result == {"degraded": 1, "offline": 1}
    assert fresh.status == "active"
    assert stale.status == "degraded"
    assert dead_stream.status == "offline"


def test_staleness_task_is_registered_routed_and_scheduled():
    staleness_worker.celery_app.loader.import_default_modules()

    assert "app.workers.staleness_worker.check_camera_staleness" in staleness_worker.celery_app.tasks
    assert (
        staleness_worker.celery_app.conf.task_routes[
            "app.workers.staleness_worker.check_camera_staleness"
        ]["queue"]
        == "inference"
    )
    assert "check-camera-staleness" in staleness_worker.celery_app.conf.beat_schedule
