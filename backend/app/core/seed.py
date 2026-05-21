"""
backend/app/core/seed.py
 
Seed script — inserts known Jogja CCTV cameras into the cameras table.
Safe to run multiple times — uses ON CONFLICT DO NOTHING (idempotent).
 
Usage:
    cd backend
    python -m app.core.seed
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Camera Data

CAMERAS = [
    {
        "name": "ATCS UTARA-TIMUR GARDENA (JL. URIP SUMOHARJO) V. TIMUR",
        "camera_id": "atcs_urip_sumoharjo",
        "stream_url": "https://cctvjss.jogjakota.go.id/atcs/ATCS_Utara-Timur_Gardena_Jl_Urip%20Sumoharjo_V_Timur.stream/playlist.m3u8",
        "referer": "https://cctv.jogjakota.go.id/",
        "longitude": 110.381315,
        "latitude": -7.782848,
        "is_active": True,
    },

    # {
    #     "name": "",
    #     "camera_id": "",
    #     "stream_url": "",
    #     "referer": "",
    #     "longitude": 0.0,
    #     "latitude": 0.0,
    #     "is_active": True,
    # },
]

# Seed Logic
async def seed_cameras(session: AsyncSession) -> None:
    inserted = 0
    skipped = 0

    for cam in CAMERAS:
        # WKT Point format: 'POINT(longitude latitude)'
        point_wkt = f"SRID=4326;POINT({cam['longitude']} {cam['latitude']})"

        result = await session.execute(
            text("""
                INSERT INTO cameras (id, name, camera_id, stream_url, referer, location, is_active)
                VALUES (
                    gen_random_uuid(),
                    :name,
                    :camera_id,
                    :stream_url,
                    :referer,
                    ST_GeomFromEWKT(:location),
                    :is_active
                )
                ON CONFLICT (camera_id) DO NOTHING
            """),
            {
                "name":       cam["name"],
                "camera_id":  cam["camera_id"],
                "stream_url": cam["stream_url"],
                "referer":    cam["referer"],
                "location":   point_wkt,
                "is_active":  cam["is_active"],
            }
        )

        if result.rowcount == 1:
            inserted += 1
            logger.info(f"  Inserted: {cam['camera_id']}")
        else:
            skipped += 1
            logger.info(f"  Skipped (already exists): {cam['camera_id']}")
 
    await session.commit()
    logger.info(f"Seed complete — {inserted} inserted, {skipped} skipped.")
 
 
async def main() -> None:
    logger.info("Starting camera seed...")
    factory = get_session_factory()
    async with factory() as session:
        await seed_cameras(session)
 
 
if __name__ == "__main__":
    asyncio.run(main())