"""Report activity-grid coverage gaps and the camera -> segment -> hex chain.

Spatial coverage gaps (hexes with no intersecting road segment) are separate
from temporal gaps: no amount of hourly interpolation fills a hex that has no
segment mapped to it, so those hexes stay legitimately ``no_data`` per the PRD's
"missing => data tidak tersedia" rule.

This also explains *why* a hex containing a CCTV can still be empty/fallback: a
camera is attributed through its mapped road segment's longest-intersection hex,
so a camera physically inside hex H can feed a different hex when its segment's
primary overlap is elsewhere. Run after `build_replay_dataset.py`.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.database import get_sync_db
from app.models.activity_grid import ActivityGridHex
from app.models.camera import Camera
from app.models.camera_road_segment import CameraRoadSegment
from app.models.road_segment import RoadSegment
from app.models.segment_emission import SegmentEmission

SAMPLE_LIMIT = 20


def _primary_hex_by_segment(db, segment_ids: list[str]) -> dict[str, int]:
    if not segment_ids:
        return {}
    overlap = func.ST_Length(func.ST_Intersection(ActivityGridHex.geometry, RoadSegment.geometry))
    rows = db.execute(
        select(RoadSegment.road_segment_id, ActivityGridHex.hex_id)
        .join(ActivityGridHex, func.ST_Intersects(ActivityGridHex.geometry, RoadSegment.geometry))
        .where(RoadSegment.road_segment_id.in_(segment_ids))
        .distinct(RoadSegment.road_segment_id)
        .order_by(RoadSegment.road_segment_id, overlap.desc())
    ).all()
    return {segment_id: hex_id for segment_id, hex_id in rows}


def _containing_hex_by_camera(db) -> dict[str, int]:
    rows = db.execute(
        select(Camera.camera_id, func.min(ActivityGridHex.hex_id))
        .join(ActivityGridHex, func.ST_Intersects(ActivityGridHex.geometry, Camera.location))
        .where(Camera.is_active.is_(True))
        .group_by(Camera.camera_id)
    ).all()
    return {camera_id: hex_id for camera_id, hex_id in rows}


def _active_mappings(db) -> list[tuple[str, str]]:
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(Camera.camera_id, RoadSegment.road_segment_id)
        .join(CameraRoadSegment, CameraRoadSegment.camera_id == Camera.id)
        .join(RoadSegment, CameraRoadSegment.road_segment_id == RoadSegment.id)
        .where(
            Camera.is_active.is_(True),
            CameraRoadSegment.is_active.is_(True),
            (CameraRoadSegment.valid_to.is_(None)) | (CameraRoadSegment.valid_to > now),
        )
    ).all()
    return [(camera_id, segment_id) for camera_id, segment_id in rows]


def report() -> dict:
    with get_sync_db() as db:
        total = db.execute(select(func.count()).select_from(ActivityGridHex)).scalar_one()
        covered = db.execute(
            select(func.count(func.distinct(ActivityGridHex.hex_id)))
            .select_from(ActivityGridHex)
            .join(RoadSegment, func.ST_Intersects(ActivityGridHex.geometry, RoadSegment.geometry))
        ).scalar_one()

        active_cameras = set(db.execute(
            select(Camera.camera_id).where(Camera.is_active.is_(True))
        ).scalars().all())
        mappings = _active_mappings(db)
        mapped_cameras = {camera_id for camera_id, _ in mappings}
        primary = _primary_hex_by_segment(db, [segment_id for _, segment_id in mappings])
        containing = _containing_hex_by_camera(db)

        off_primary = [
            {"camera_id": camera_id, "segment_id": segment_id,
             "containing_hex": containing.get(camera_id), "primary_hex": primary.get(segment_id)}
            for camera_id, segment_id in mappings
            if containing.get(camera_id) is not None
            and primary.get(segment_id) is not None
            and containing[camera_id] != primary[segment_id]
        ]
        unmapped = sorted(active_cameras - mapped_cameras)

        segments_with_replay = set(db.execute(
            select(RoadSegment.road_segment_id)
            .join(SegmentEmission, SegmentEmission.road_segment_id == RoadSegment.id)
            .where(SegmentEmission.ahp_metadata["source_mode"].astext == "REPLAY")
            .distinct()
        ).scalars().all())
        all_segments = set(db.execute(select(RoadSegment.road_segment_id)).scalars().all())

    return {
        "grid": {
            "total_hexes": int(total),
            "hexes_with_segment": int(covered),
            "hexes_without_segment": int(total) - int(covered),
        },
        "cameras": {
            "active": len(active_cameras),
            "with_active_mapping": len(mapped_cameras),
            "without_active_mapping": len(unmapped),
            "without_active_mapping_sample": unmapped[:SAMPLE_LIMIT],
            "feeding_a_different_hex_than_they_sit_in": len(off_primary),
            "off_primary_sample": off_primary[:SAMPLE_LIMIT],
        },
        "replay": {
            "segments_total": len(all_segments),
            "segments_with_replay": len(segments_with_replay),
            "segments_without_replay": len(all_segments - segments_with_replay),
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(report(), indent=2, ensure_ascii=False))
