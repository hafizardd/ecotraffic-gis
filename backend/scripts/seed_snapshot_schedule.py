"""One-off schedule seed for the historical snapshot sampler (M4).

Assigns each non-LIVE camera a processing priority from its mapped road
segment's ``priority_tier`` (Sangat Tinggi/Tinggi -> high, Sedang -> medium,
Rendah/Sangat Rendah -> low) and staggers ``next_sample_at`` by a random
fraction of the camera's effective interval so callers do not all become due
in the same cycle. Idempotent to re-run; re-running re-staggers.

Usage:
    python -m scripts.seed_snapshot_schedule
"""

from datetime import datetime, timedelta, timezone
import argparse
import random

from sqlalchemy import select, text

from app.core.database import get_sync_db
from app.models.camera import Camera
from app.workers.snapshot_worker import _effective_interval

PRIORITY_SQL = text("""
    UPDATE cameras c
    SET priority = COALESCE(
        CASE lower(s.priority_tier)
            WHEN 'sangat tinggi' THEN 'high'
            WHEN 'tinggi' THEN 'high'
            WHEN 'sedang' THEN 'medium'
            WHEN 'rendah' THEN 'low'
            WHEN 'sangat rendah' THEN 'low'
        END, 'medium')
    FROM (
        SELECT DISTINCT ON (crs.camera_id)
               crs.camera_id AS camera_db_id,
               rs.spatial_metadata->>'priority_tier' AS priority_tier
        FROM camera_road_segments crs
        JOIN road_segments rs ON rs.id = crs.road_segment_id
        WHERE crs.is_active
        ORDER BY crs.camera_id, crs.is_active DESC
    ) s
    WHERE c.id = s.camera_db_id AND c.data_source <> 'LIVE' AND c.is_active
""")


def seed(seed_value: int | None = None, dry_run: bool = False) -> dict:
    rng = random.Random(seed_value)
    with get_sync_db() as db:
        db.execute(PRIORITY_SQL)
        cameras = db.execute(
            select(Camera).where(Camera.data_source != "LIVE", Camera.is_active.is_(True))
        ).scalars().all()
        now = datetime.now(timezone.utc)
        priorities = {"high": 0, "medium": 0, "low": 0}
        for camera in cameras:
            interval = _effective_interval(camera.priority, camera.sampling_interval_seconds)
            priorities[camera.priority] = priorities.get(camera.priority, 0) + 1
            if dry_run:
                continue
            camera.next_sample_at = now + timedelta(seconds=rng.uniform(0, interval))
        if not dry_run:
            db.flush()
        return {"cameras": len(cameras), "priorities": priorities, "dry_run": dry_run}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(f"Seeded snapshot schedule: {seed(seed_value=args.seed, dry_run=args.dry_run)}")
