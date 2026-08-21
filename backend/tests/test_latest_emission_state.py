import asyncio
from datetime import datetime, timezone
import json

from app.services.emission_aggregation import EmissionObservation, EmissionWindowAggregator
from app.services.latest_emission_state import (
    AsyncLatestEmissionStateStore,
    LatestEmissionStateStore,
)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.writes = []

    def setex(self, key, ttl_seconds, value):
        self.writes.append((key, ttl_seconds, value))
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    async def mget(self, keys):
        return [self.values.get(key) for key in keys]


def _aggregate():
    observation = EmissionObservation(
        camera_id="camera-1",
        camera_database_id="database-camera-1",
        job_id="job-1",
        captured_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
        vehicle_counts={"car": 4, "motorcycle": 2, "bus": 1, "truck": 0},
        frame_acquisition_latency_s=1,
        queue_wait_s=2,
        inference_latency_s=3,
        cycle_duration_s=6,
    )
    return EmissionWindowAggregator(window_seconds=60).add(observation).current


def test_latest_state_store_writes_flat_aggregated_payload_with_ttl():
    redis_client = FakeRedis()
    store = LatestEmissionStateStore(redis_client, ttl_seconds=3600)

    payload = store.save(_aggregate())

    assert redis_client.writes[0][0] == "emission:camera:camera-1"
    assert redis_client.writes[0][1] == 3600
    assert payload["car"] == 4
    assert payload["motorcycle"] == 2
    assert payload["sample_count"] == 1
    assert payload["aggregation_method"] == "arithmetic_mean_of_snapshot_counts"
    assert payload["vehicle_count_semantics"] == "mean_observed_snapshot_count"
    assert payload["timestamp"] == "2026-08-21T12:00:00+00:00"
    assert payload["total_co_g_per_min"] > 0
    assert store.get("camera-1") == payload


def test_latest_state_store_decodes_bytes_and_rejects_non_object_payloads():
    payload = {"camera_id": "camera-1"}

    assert LatestEmissionStateStore.decode(json.dumps(payload).encode()) == payload
    assert LatestEmissionStateStore.decode(None) is None

    try:
        LatestEmissionStateStore.decode("[]")
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("list payloads must be rejected")


def test_async_latest_state_store_reads_all_cameras_in_one_mget_and_skips_bad_data():
    redis_client = FakeRedis()
    redis_client.values = {
        "emission:camera:camera-1": json.dumps({"camera_id": "camera-1"}),
        "emission:camera:camera-2": "not-json",
    }

    states = asyncio.run(
        AsyncLatestEmissionStateStore(redis_client).get_many(
            ["camera-1", "camera-2", "camera-3"]
        )
    )

    assert states == {"camera-1": {"camera_id": "camera-1"}}
