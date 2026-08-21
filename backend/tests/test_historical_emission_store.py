from datetime import datetime, timezone
import uuid

from app.services.emission_aggregation import EmissionObservation, EmissionWindowAggregator
from app.services.historical_emission_store import HistoricalEmissionStore


def _aggregate():
    return EmissionWindowAggregator(window_seconds=60).add(
        EmissionObservation(
            camera_id="camera-1",
            camera_database_id="12345678-1234-5678-1234-567812345678",
            job_id="job-1",
            captured_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
            vehicle_counts={"car": 6, "motorcycle": 2, "bus": 1, "truck": 0},
            frame_acquisition_latency_s=1,
            queue_wait_s=2,
            inference_latency_s=3,
            cycle_duration_s=6,
        )
    ).current


def test_historical_row_preserves_window_mean_semantics():
    row = HistoricalEmissionStore.row_for(_aggregate())

    assert isinstance(row["id"], uuid.UUID)
    assert row["camera_id"] == uuid.UUID("12345678-1234-5678-1234-567812345678")
    assert row["sample_count"] == 1
    assert row["aggregation_method"] == "arithmetic_mean_of_snapshot_counts"
    assert row["vehicle_count_semantics"] == "mean_observed_snapshot_count"
    assert row["car"] == 6
    assert row["total_nox_g_per_min"] > 0
    assert row["cycle_duration_s"] == 6


def test_historical_store_skips_empty_completed_windows():
    calls = []
    store = HistoricalEmissionStore(session_factory=lambda: calls.append("session"))

    assert store.save_many([]) == 0
    assert calls == []
