from datetime import datetime, timedelta, timezone

from app.services.data_freshness import (
    FreshnessPolicy,
    FreshnessStatus,
    classify_freshness,
)


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
POLICY = FreshnessPolicy(fresh_threshold_seconds=30, aging_threshold_seconds=90)


def test_freshness_boundaries_match_the_configured_windows():
    assert classify_freshness(NOW - timedelta(seconds=30), now=NOW, policy=POLICY).status is FreshnessStatus.FRESH
    assert classify_freshness(NOW - timedelta(seconds=31), now=NOW, policy=POLICY).status is FreshnessStatus.AGING
    assert classify_freshness(NOW - timedelta(seconds=90), now=NOW, policy=POLICY).status is FreshnessStatus.AGING
    assert classify_freshness(NOW - timedelta(seconds=91), now=NOW, policy=POLICY).status is FreshnessStatus.STALE


def test_freshness_handles_missing_and_future_timestamps_safely():
    unknown = classify_freshness(None, now=NOW, policy=POLICY)
    future = classify_freshness(NOW + timedelta(seconds=10), now=NOW, policy=POLICY)

    assert unknown.status is FreshnessStatus.UNKNOWN
    assert unknown.age_seconds is None
    assert future.status is FreshnessStatus.FRESH
    assert future.age_seconds == 0
