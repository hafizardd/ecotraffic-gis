"""Redis-backed current emission state for low-latency reads."""

from collections.abc import Mapping
from datetime import datetime, timezone
import json
from typing import Any

from app.services.emission_aggregation import AggregatedEmission, EMISSION_RATE_FIELDS, VEHICLE_TYPES


class LatestEmissionStateStore:
    """Store the latest aggregated emission state for each camera."""

    def __init__(self, redis_client: Any, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    def save(self, emission: AggregatedEmission) -> dict[str, Any]:
        payload = self.payload_for(emission)
        self.redis.setex(
            self.key_for(emission.camera_id),
            self.ttl_seconds,
            json.dumps(payload, separators=(",", ":")),
        )
        return payload

    def get(self, camera_id: str) -> dict[str, Any] | None:
        return self.decode(self.redis.get(self.key_for(camera_id)))

    @staticmethod
    def key_for(camera_id: str) -> str:
        return f"emission:camera:{camera_id}"

    @staticmethod
    def payload_for(emission: AggregatedEmission) -> dict[str, Any]:
        aggregate = emission.to_payload()
        vehicle_count = aggregate["vehicle_count"]
        emission_values = aggregate["emission"]
        last_captured_at = aggregate["last_captured_at"]
        return {
            "camera_id": emission.camera_id,
            "camera_database_id": emission.camera_database_id,
            "timestamp": last_captured_at,
            "captured_at": last_captured_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "period_start": aggregate["period_start"],
            "period_end": aggregate["period_end"],
            "sample_count": aggregate["sample_count"],
            "aggregation_method": aggregate["aggregation_method"],
            "vehicle_count_semantics": aggregate["vehicle_count_semantics"],
            **{vehicle_type: vehicle_count[vehicle_type] for vehicle_type in VEHICLE_TYPES},
            **{field: emission_values[field] for field in EMISSION_RATE_FIELDS},
            "frame_acquisition_latency_s": aggregate[
                "mean_frame_acquisition_latency_s"
            ],
            "queue_wait_s": aggregate["mean_queue_wait_s"],
            "inference_latency_s": aggregate["mean_inference_latency_s"],
            "cycle_duration_s": aggregate["mean_cycle_duration_s"],
        }

    @staticmethod
    def decode(value: str | bytes | None) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        decoded = json.loads(value)
        if not isinstance(decoded, Mapping):
            raise ValueError("latest emission state must be a JSON object")
        return dict(decoded)


class AsyncLatestEmissionStateStore:
    """Async counterpart used by request handlers without blocking the event loop."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    async def get_many(self, camera_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not camera_ids:
            return {}
        values = await self.redis.mget(
            [LatestEmissionStateStore.key_for(camera_id) for camera_id in camera_ids]
        )
        states = {}
        for camera_id, value in zip(camera_ids, values, strict=True):
            try:
                state = LatestEmissionStateStore.decode(value)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                continue
            if state is not None:
                states[camera_id] = state
        return states
