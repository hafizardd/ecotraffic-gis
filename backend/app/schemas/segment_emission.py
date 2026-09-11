from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SegmentEmissionResponse(BaseModel):
    road_segment_id: str
    name: str
    length_km: float
    period_start: datetime | None
    period_end: datetime | None
    calculated_at: datetime | None
    raw_counts: dict[str, Any] | None
    volume_per_hour: dict[str, Any] | None
    vkt_km_h: dict[str, Any] | None
    pollutant_totals_g_h: dict[str, Any] | None
    category_pollutant_breakdown_g_h: dict[str, Any] | None
    provenance: dict[str, Any]
    volume_status: str = "calculated"
    vehicle_count_semantics: str = "interval_count"
    freshness_status: str = "unknown"
    population: int | None = None
    population_district: str | None = None
    population_context: dict[str, Any] | None = None


class SegmentEmissionMapItem(BaseModel):
    road_segment_id: str
    total_emission: float | None
    calculated_at: datetime | None = None
    observed_at: datetime | None = None
    data_age_seconds: int | None = None
    freshness_status: str = "unknown"
    vehicle_count_semantics: str = "unknown"
    source_cameras: list[str] = []
