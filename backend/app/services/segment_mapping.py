"""Resolve explicit CCTV camera-to-road-segment stream mappings."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import Camera
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment


@dataclass(frozen=True, slots=True)
class CameraSegmentMapping:
    camera_id: str
    road_segment_id: str
    lane_or_stream_id: str
    is_active: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def applies_at(self, captured_at: datetime) -> bool:
        return (
            self.is_active
            and (self.valid_from is None or captured_at >= self.valid_from)
            and (self.valid_to is None or captured_at < self.valid_to)
        )


class MappingResolutionError(ValueError):
    pass


def resolve_camera_mapping(
    mappings: list[CameraSegmentMapping],
    *,
    camera_id: str,
    captured_at: datetime,
) -> CameraSegmentMapping:
    """Resolve exactly one active mapping for a camera and capture time."""
    matches = [
        mapping
        for mapping in mappings
        if mapping.camera_id == camera_id and mapping.applies_at(captured_at)
    ]
    if not matches:
        raise MappingResolutionError(
            f"no active road-segment mapping for camera {camera_id}"
        )
    if len(matches) > 1:
        raise MappingResolutionError(
            f"ambiguous active road-segment mapping for camera {camera_id}"
        )
    return matches[0]


async def load_active_mappings(db: AsyncSession) -> list[CameraSegmentMapping]:
    """Load active database mappings using stable public identifiers."""
    result = await db.execute(
        select(Camera.camera_id, RoadSegment.road_segment_id,
               CameraRoadSegment.lane_or_stream_id, CameraRoadSegment.is_active,
               CameraRoadSegment.valid_from, CameraRoadSegment.valid_to)
        .join(CameraRoadSegment, CameraRoadSegment.camera_id == Camera.id)
        .join(RoadSegment, CameraRoadSegment.road_segment_id == RoadSegment.id)
        .where(CameraRoadSegment.is_active.is_(True))
    )
    return [CameraSegmentMapping(*row) for row in result.all()]
