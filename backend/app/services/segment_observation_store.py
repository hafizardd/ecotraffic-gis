"""Mapping between validated observations and persistence rows."""

import uuid
from typing import Any

from app.services.segment_observation import SegmentTrafficObservation
from app.models.segment_traffic_observation import SegmentTrafficObservationRecord
from sqlalchemy.ext.asyncio import AsyncSession


def observation_row(
    observation: SegmentTrafficObservation,
    *,
    road_segment_database_id: uuid.UUID | str,
    camera_database_id: uuid.UUID | str,
    ingested_at: Any = None,
) -> dict[str, Any]:
    row = {
        "id": uuid.uuid4(),
        "road_segment_id": uuid.UUID(str(road_segment_database_id)),
        "camera_id": uuid.UUID(str(camera_database_id)),
        "camera_identifier": observation.camera_id,
        "lane_or_stream_id": observation.lane_or_stream_id,
        "captured_at": observation.captured_at,
        "observation_duration_seconds": observation.observation_duration_seconds,
        "vehicle_count_semantics": observation.vehicle_count_semantics.value,
        "raw_detected_count": dict(observation.raw_detected_count),
    }
    if ingested_at is not None:
        row["ingested_at"] = ingested_at
    return row


async def persist_observation(
    db: AsyncSession,
    observation: SegmentTrafficObservation,
    segment_database_id: uuid.UUID,
    camera_database_id: uuid.UUID,
) -> SegmentTrafficObservationRecord:
    record = SegmentTrafficObservationRecord(**observation_row(
        observation,
        road_segment_database_id=segment_database_id,
        camera_database_id=camera_database_id,
    ))
    db.add(record)
    await db.flush()
    return record
