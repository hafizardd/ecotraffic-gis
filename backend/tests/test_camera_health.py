from datetime import datetime, timedelta, timezone

from app.services.camera_health import CameraHealthPolicy, CameraHealthStatus


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
