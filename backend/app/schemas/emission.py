import uuid
from datetime import datetime

from pydantic import BaseModel

class EmissionRow(BaseModel):
    """Single emission record — one detection cycle."""
    id: uuid.UUID
    timestamp: datetime
    car: float
    motorcycle: float
    bus: float
    truck: float
    total_tsp_g_per_min: float
    total_tsp_kg_per_hr: float
    total_nox_g_per_min: float
    total_nox_kg_per_hr: float
    total_so2_g_per_min: float
    total_so2_kg_per_hr: float
    total_hc_g_per_min: float
    total_hc_kg_per_hr: float
    total_co_g_per_min: float
    total_co_kg_per_hr: float
    total_co2_g_per_min: float
    total_co2_kg_per_hr: float
    total_ch4_g_per_min: float
    total_ch4_kg_per_hr: float
    total_n2o_g_per_min: float
    total_n2o_kg_per_hr: float

    cycle_duration_s: float
 
    model_config = {"from_attributes": True}
 
 
class CameraEmissionsResponse(BaseModel):
    """Response for GET /api/cameras/{camera_id}/emissions."""
    camera_id: str
    total_records: int
    emissions: list[EmissionRow]
 
 
class VehicleSummary(BaseModel):
    """Aggregated vehicle counts across all cameras."""
    car: int
    motorcycle: int
    bus: int
    truck: int
 
 
class EmissionSummaryResponse(BaseModel):
    """Response for GET /api/emissions/summary — city-wide totals."""
    total_cameras_active: int
    total_tsp_g_per_min: float
    total_tsp_kg_per_hr: float
    total_nox_g_per_min: float
    total_nox_kg_per_hr: float
    total_so2_g_per_min: float
    total_so2_kg_per_hr: float
    total_hc_g_per_min: float
    total_hc_kg_per_hr: float
    total_co_g_per_min: float
    total_co_kg_per_hr: float
    total_co2_g_per_min: float
    total_co2_kg_per_hr: float
    total_ch4_g_per_min: float
    total_ch4_kg_per_hr: float
    total_n2o_g_per_min: float
    total_n2o_kg_per_hr: float
    by_vehicle: VehicleSummary
    last_updated: datetime | None
    active_cameras: int = 0
    live_cameras: int = 0
    historical_cameras: int = 0
    fresh_camera_states: int = 0
    stale_camera_states: int = 0
    latest_observation_at: datetime | None = None
    latest_processing_at: datetime | None = None
    source: str = "emission_aggregates"
    freshness_status: str = "unknown"
