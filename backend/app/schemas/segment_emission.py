from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SegmentEmissionResponse(BaseModel):
    road_segment_id: str
    name: str
    length_km: float
    period_start: datetime
    period_end: datetime
    calculated_at: datetime
    raw_counts: dict[str, Any]
    volume_per_hour: dict[str, Any] | None
    vkt_km_h: dict[str, Any] | None
    pollutant_totals_g_h: dict[str, Any]
    category_pollutant_breakdown_g_h: dict[str, Any]
    raw_criteria: dict[str, Any]
    normalized_criteria: dict[str, Any] | None
    decision_score: float | None
    priority: str | None
    spatial_criteria_status: str
    provenance: dict[str, Any]
    ahp_metadata: dict[str, Any]
    volume_status: str = "calculated"
    vehicle_count_semantics: str = "interval_count"
    freshness_status: str = "unknown"


class SegmentEmissionMapItem(BaseModel):
    road_segment_id: str
    decision_score: float | None
    priority: str | None
    total_emission: float | None
    calculated_at: datetime
