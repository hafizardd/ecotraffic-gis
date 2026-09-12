from datetime import datetime, timedelta, timezone

from app.services.emission_aggregation import EmissionObservation, EmissionWindowAggregator
from app.services.historical_emission_store import HistoricalEmissionStore
from app.services.latest_emission_state import LatestEmissionStateStore


class _Redis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _ttl_seconds, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


def _observation(captured_at: datetime, *, car: int) -> EmissionObservation:
    return EmissionObservation(
        camera_id="camera-1",
        camera_database_id="12345678-1234-5678-1234-567812345678",
        job_id=f"job-{captured_at.timestamp()}",
        captured_at=captured_at,
        vehicle_counts={"car": car, "motorcycle": 2, "bus": 0, "truck": 1},
        frame_acquisition_latency_s=1,
        queue_wait_s=2,
        inference_latency_s=3,
        cycle_duration_s=6,
    )


def test_aggregate_pipeline_produces_latest_and_historical_window_records():
    start = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    aggregator = EmissionWindowAggregator(window_seconds=60)
    aggregator.add(_observation(start, car=4))
    update = aggregator.add(_observation(start + timedelta(seconds=60), car=8))

    latest_store = LatestEmissionStateStore(_Redis(), ttl_seconds=3600)
    latest = latest_store.save(update.current)
    historical = HistoricalEmissionStore.row_for(update.completed[0])

    assert latest["camera_id"] == "camera-1"
    assert str(historical["camera_id"]) == "12345678-1234-5678-1234-567812345678"
    assert latest["car"] == 8
    assert historical["car"] == 4
    assert historical["sample_count"] == 1
    assert latest["total_co_g_per_min"] > 0
    assert historical["total_co_g_per_min"] > 0
