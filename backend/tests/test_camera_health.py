from datetime import datetime, timedelta, timezone

from types import SimpleNamespace

import pytest

from app.services import camera_health
from app.services.camera_health import CameraHealthPolicy, CameraHealthService, CameraHealthStatus


POLICY = CameraHealthPolicy(
    retry_base_seconds=5,
    retry_max_seconds=60,
    failures_before_offline=4,
)


def test_retry_backoff_is_bounded_and_progressive():
    assert [POLICY.retry_delay_seconds(count) for count in range(1, 7)] == [
        5,
        10,
        20,
        40,
        60,
        60,
    ]


def test_health_is_degraded_before_becoming_offline():
    assert POLICY.status_for_failure_count(1) is CameraHealthStatus.DEGRADED
    assert POLICY.status_for_failure_count(3) is CameraHealthStatus.DEGRADED
    assert POLICY.status_for_failure_count(4) is CameraHealthStatus.OFFLINE


def test_failure_update_carries_the_next_retry_time():
    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    delay = POLICY.retry_delay_seconds(2)

    assert delay == 10
    assert now + timedelta(seconds=delay) == datetime(
        2026,
        8,
        21,
        0,
        0,
        10,
        tzinfo=timezone.utc,
    )


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_capture_failure_then_success_updates_persisted_health(monkeypatch):
    camera = SimpleNamespace(
        failure_count=3,
        status="degraded",
        last_sample_at=None,
        last_success_at=None,
        last_error_at=None,
        next_sample_at=None,
    )
    monkeypatch.setattr(camera_health, "get_sync_db", lambda: _Session())
    monkeypatch.setattr(
        CameraHealthService,
        "_locked_camera",
        staticmethod(lambda _db, _camera_id: camera),
    )
    service = CameraHealthService(POLICY)
    failed_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

    update = service.record_capture_failure("12345678-1234-5678-1234-567812345678", failed_at)

    assert update is not None
    assert update.status is CameraHealthStatus.OFFLINE
    assert update.retry_delay_seconds == 40
    assert camera.next_sample_at == failed_at + timedelta(seconds=40)
    assert camera.last_error_at == failed_at

    recovered_at = failed_at + timedelta(seconds=41)
    service.record_capture_success("12345678-1234-5678-1234-567812345678", recovered_at)

    assert camera.status == CameraHealthStatus.ACTIVE.value
    assert camera.failure_count == 0
    assert camera.last_success_at == recovered_at


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def _stale_camera(**overrides):
    defaults = {
        "camera_id": "camera-1",
        "data_source": "LIVE",
        "status": "active",
        "last_success_at": NOW - timedelta(seconds=200),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_staleness_policy_rejects_offline_below_stale_threshold():
    with pytest.raises(ValueError, match="offline_threshold_seconds"):
        CameraHealthPolicy(
            retry_base_seconds=5,
            retry_max_seconds=60,
            failures_before_offline=4,
            stale_threshold_seconds=90,
            offline_threshold_seconds=30,
        )


def test_unsampled_historical_camera_is_marked_offline():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(data_source="HISTORICAL", last_success_at=None)

    assert service.degrade_by_staleness(camera, NOW) is CameraHealthStatus.OFFLINE
    assert camera.status == "offline"


def test_unsampled_historical_camera_already_offline_is_unchanged():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(data_source="HISTORICAL", last_success_at=None, status="offline")

    assert service.degrade_by_staleness(camera, NOW) is None
    assert camera.status == "offline"


def test_unsampled_live_camera_waits_for_first_capture():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=None)

    assert service.degrade_by_staleness(camera, NOW) is None
    assert camera.status == "active"


def test_fresh_camera_is_not_degraded():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=NOW - timedelta(seconds=20))

    assert service.degrade_by_staleness(camera, NOW) is None
    assert camera.status == "active"


def test_stale_active_camera_becomes_degraded():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=NOW - timedelta(seconds=120))

    assert service.degrade_by_staleness(camera, NOW) is CameraHealthStatus.DEGRADED
    assert camera.status == "degraded"


def test_stale_degraded_camera_is_not_downgraded_twice():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=NOW - timedelta(seconds=120), status="degraded")

    assert service.degrade_by_staleness(camera, NOW) is None
    assert camera.status == "degraded"


def test_very_stale_active_camera_becomes_offline():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=NOW - timedelta(seconds=400))

    assert service.degrade_by_staleness(camera, NOW) is CameraHealthStatus.OFFLINE
    assert camera.status == "offline"


def test_very_stale_degraded_camera_becomes_offline():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=NOW - timedelta(seconds=400), status="degraded")

    assert service.degrade_by_staleness(camera, NOW) is CameraHealthStatus.OFFLINE
    assert camera.status == "offline"


def test_very_stale_offline_camera_is_unchanged():
    service = CameraHealthService(POLICY)
    camera = _stale_camera(last_success_at=NOW - timedelta(seconds=400), status="offline")

    assert service.degrade_by_staleness(camera, NOW) is None
    assert camera.status == "offline"
