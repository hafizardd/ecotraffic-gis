import uuid
from datetime import datetime

from pydantic import BaseModel

class EmissionRow(BaseModel):
    """Single emission record — one detection cycle."""
    id: uuid.UUID
    timestamp: datetime
    car: int
    motorcycle: int
    bus: int
    truck: int
    total_co_g_per_min: float
    total_co_kg_per_hr: float
    total_nox_g_per_min: float
    total_nox_kg_per_hr: float
    total_pm_g_per_min: float
    total_pm_kg_per_hr: float
    total_nmvoc_g_per_min: float
    total_nmvoc_kg_per_hr: float

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
    total_co_g_per_min: float
    total_co_kg_per_hr: float
    total_nox_g_per_min: float
    total_nox_kg_per_hr: float
    total_pm_g_per_min: float
    total_pm_kg_per_hr: float
    total_nmvoc_g_per_min: float
    total_nmvoc_kg_per_hr: float
    by_vehicle: VehicleSummary
    last_updated: datetime | None