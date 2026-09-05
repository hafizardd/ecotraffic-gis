"""Idempotent road-segment and camera mapping seed helpers."""

import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cctv import CAMERAS

logger = logging.getLogger(__name__)
GEOJSON_PATH = Path(__file__).resolve().parents[2] / "data" / "road_segments_scored.geojson"


def load_segment_features(path: Path = GEOJSON_PATH) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        collection = json.load(handle)
    if collection.get("type") != "FeatureCollection":
        raise ValueError("segment GeoJSON must be a FeatureCollection")
    return collection["features"]


async def seed_road_segments(session: AsyncSession, path: Path = GEOJSON_PATH) -> tuple[int, int]:
    inserted = skipped = 0
    for feature in load_segment_features(path):
        props = feature.get("properties", {})
        segment_id = props.get("segment_id")
        if not segment_id or feature.get("geometry", {}).get("type") != "LineString":
            raise ValueError("each segment feature requires a LineString and segment_id")
        result = await session.execute(text("""
            INSERT INTO road_segments (id, road_segment_id, name, geometry, length_km, spatial_metadata)
            VALUES (gen_random_uuid(), :segment_id, :name,
                    ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326), :length_km, CAST(:metadata AS jsonb))
            ON CONFLICT (road_segment_id) DO NOTHING
        """), {
            "segment_id": segment_id,
            "name": props.get("nama_ruas", segment_id),
            "geometry": json.dumps(feature["geometry"]),
            "length_km": float(props.get("length_km", 0)),
            "metadata": json.dumps({"source": "geojson_import", "priority_tier": props.get("priority_tier"), "volume_per_hour": props.get("volume_per_hour")}),
        })
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1
    await session.commit()
    logger.info("road segment seed complete: %s inserted, %s skipped", inserted, skipped)
    return inserted, skipped


async def seed_camera_segment_mappings(session: AsyncSession) -> int:
    created = 0
    for camera in CAMERAS:
        result = await session.execute(text("""
            INSERT INTO camera_road_segments (id, camera_id, road_segment_id, lane_or_stream_id, is_active)
            SELECT gen_random_uuid(), c.id, s.id, 'default', true
            FROM cameras c
            CROSS JOIN LATERAL (
                SELECT id FROM road_segments
                ORDER BY ST_Distance(geometry, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
                LIMIT 1
            ) s
            WHERE c.camera_id = :camera_id
              AND NOT EXISTS (
                  SELECT 1 FROM camera_road_segments existing
                  WHERE existing.camera_id = c.id
                    AND existing.road_segment_id = s.id
                    AND existing.lane_or_stream_id = 'default'
                    AND existing.valid_from IS NULL
              )
        """), camera)
        created += max(result.rowcount, 0)
    await session.commit()
    logger.info("camera segment mapping seed complete: %s created", created)
    return created
