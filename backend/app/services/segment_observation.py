"""Validated input contract for segment-level traffic observations."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math

from cv.proposal_emission_factors import VEHICLE_CATEGORIES


class VehicleCountSemantics(str, Enum):
    INTERVAL_COUNT = "interval_count"
    SNAPSHOT_OCCUPANCY = "snapshot_occupancy"
    VEHICLES_PER_HOUR = "vehicles_per_hour"


@dataclass(frozen=True, slots=True)
class SegmentTrafficObservation:
    camera_id: str
    road_segment_id: str
    lane_or_stream_id: str
    captured_at: datetime
    observation_duration_seconds: float
    raw_detected_count: Mapping[str, int | float]
    vehicle_count_semantics: VehicleCountSemantics = VehicleCountSemantics.INTERVAL_COUNT

    def __post_init__(self) -> None:
        if not self.camera_id or not self.road_segment_id or not self.lane_or_stream_id:
            raise ValueError("camera_id, road_segment_id, and lane_or_stream_id are required")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        if not math.isfinite(self.observation_duration_seconds) or self.observation_duration_seconds <= 0:
            raise ValueError("observation_duration_seconds must be finite and greater than zero")

        counts = {}
        for category in VEHICLE_CATEGORIES:
            value = float(counts[category])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"raw count for {category} must be finite and non-negative")
            counts[category] = value
        object.__setattr__(self, "raw_detected_count", counts)

    def to_payload(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "road_segment_id": self.road_segment_id,
            "lane_or_stream_id": self.lane_or_stream_id,
            "captured_at": self.captured_at.isoformat(),
            "observation_duration_seconds": self.observation_duration_seconds,
            "raw_detected_count": dict(self.raw_detected_count),
            "vehicle_count_semantics": self.vehicle_count_semantics.value,
        }
