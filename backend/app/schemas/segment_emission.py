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
    volume_per_hour: dict[str, Any]
    vkt_km_h: dict[str, Any]
    pollutant_totals_g_h: dict[str, Any]
    category_pollutant_breakdown_g_h: dict[str, Any]
    raw_criteria: dict[str, Any]
    normalized_criteria: dict[str, Any]
    decision_score: float | None
    priority: str | None
    spatial_criteria_status: str
    provenance: dict[str, Any]
    ahp_metadata: dict[str, Any]


class SegmentEmissionMapItem(BaseModel):
    road_segment_id: str
    decision_score: float | None
    priority: str | None
    total_emission: float
    calculated_at: datetime
