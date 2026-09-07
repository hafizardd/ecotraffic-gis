"""Generate one day of synthetic historical segment emissions."""

from datetime import datetime, timedelta, timezone
import random

from sqlalchemy import select

from app.core.database import get_sync_db
from app.models.camera import Camera
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment
from app.services.segment_emission_pipeline import calculate_segment_emission
from app.services.segment_emission_store import persist_segment_emission_sync
from app.services.segment_observation import SegmentTrafficObservation
from app.services.spatial_integration import compute_all_spatial_criteria


def generate(seed: int | None = None) -> int:
    rng = random.Random(seed)
    created = 0
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    with get_sync_db() as db:
        rows = db.execute(select(Camera, CameraRoadSegment, RoadSegment).join(
            CameraRoadSegment, CameraRoadSegment.camera_id == Camera.id
        ).join(RoadSegment, CameraRoadSegment.road_segment_id == RoadSegment.id).where(
            Camera.data_source != "LIVE", CameraRoadSegment.is_active.is_(True)
        )).all()
        for camera, mapping, segment in rows:
            spatial = compute_all_spatial_criteria(db, segment)
            segment.spatial_metadata = {**(segment.spatial_metadata or {}), "raw_values": spatial["raw_values"], "population_context": spatial["population_context"], "spatial_criteria_details": spatial["spatial_criteria_details"], "component_status": spatial["component_status"], "provenance": spatial["provenance"]}
            primary = (spatial["population_context"] or {}).get("primary")
            segment.population = primary.get("population") if primary else None
            base = float((segment.spatial_metadata or {}).get("volume_per_hour") or 100)
            for hour in range(24):
                period_end = end - timedelta(hours=hour)
                period_start = period_end - timedelta(minutes=1)
                total = max(0, round(base * (0.8 + rng.random() * 0.4) / 60))
                counts = {"motorcycle": round(total * .60), "car": round(total * .25), "bus": round(total * .08), "truck": round(total * .07)}
                observation = SegmentTrafficObservation(camera.camera_id, segment.road_segment_id, mapping.lane_or_stream_id, period_start, 60, counts)
                result = calculate_segment_emission([observation], period_start=period_start, period_end=period_end, road_length_km=segment.length_km, spatial_criteria=spatial["raw_values"], spatial_details=spatial)
                result["data_source"] = "HISTORICAL"
                persist_segment_emission_sync(db, segment.id, result)
                created += 1
    return created


if __name__ == "__main__":
    print(f"Generated {generate()} historical segment records")
