"""Snapshot sampler scheduling helpers (claim cadence)."""

from app.core.config import settings
from app.workers.snapshot_worker import _effective_interval


def test_effective_interval_follows_priority():
    assert _effective_interval("high", None) == settings.SNAPSHOT_HIGH_INTERVAL_SECONDS
    assert _effective_interval("medium", None) == settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS
    assert _effective_interval("low", None) == settings.SNAPSHOT_LOW_INTERVAL_SECONDS
    assert _effective_interval(None, None) == settings.SNAPSHOT_MEDIUM_INTERVAL_SECONDS


def test_effective_interval_per_camera_override_wins():
    assert _effective_interval("high", 42) == 42
