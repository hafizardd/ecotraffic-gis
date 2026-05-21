import uuid
from datetime import datetime

from pydantic import BaseModel

class CameraProperties(BaseModel):
    """Properties block inside a GeoJSON Feature."""
    id: uuid.UUID
    name: str
    camera_id: str
    stream_url: str
    is_active: bool
    created_at: datetime
 
    model_config = {"from_attributes": True}
 
 
class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]
 
 
class CameraFeature(BaseModel):
    """Single GeoJSON Feature representing one camera."""
    type: str = "Feature"
    geometry: GeoJSONPoint
    properties: CameraProperties
 
 
class CameraFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection — returned by GET /api/cameras."""
    type: str = "FeatureCollection"
    features: list[CameraFeature]