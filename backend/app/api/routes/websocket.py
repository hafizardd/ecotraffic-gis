import asyncio
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_session_factory
from app.models.camera import Camera
from app.models.emission import Emission
from app.models.road_segment import RoadSegment
from app.services.data_freshness import FreshnessPolicy, add_freshness
from app.services.latest_emission_state import AsyncLatestEmissionStateStore

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------
# Connection Manager
# ------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        stale = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                stale.add(connection)
        self.active_connections -= stale


manager = ConnectionManager()


# ------------------------------------------------------------------
# Initial state — send latest emission per camera to new client only
# ------------------------------------------------------------------

async def send_initial_state(websocket: WebSocket) -> None:
    """
    On new client connect, immediately send cached latest state for each active
    camera. History is queried once only for cache misses during a deployment
    transition or after state expiry.
    """
    try:
        factory = get_session_factory()
        async with factory() as db:
            cam_result = await db.execute(
                select(Camera).where(Camera.is_active == True)  # noqa: E712
            )
            cameras = cam_result.scalars().all()
            camera_ids = [camera.camera_id for camera in cameras]

            cached = {}
            client = None
            try:
                client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                cached = await AsyncLatestEmissionStateStore(
                    client,
                    freshness_policy=FreshnessPolicy.from_settings(settings),
                ).get_many(camera_ids)
            except Exception:
                logger.warning("latest_emission_state_unavailable", exc_info=True)
            finally:
                if client is not None:
                    await client.aclose()

            missing = [camera for camera in cameras if camera.camera_id not in cached]
            fallback_by_database_id = {}
            if missing:
                fallback_result = await db.execute(
                    select(Emission)
                    .where(Emission.camera_id.in_([camera.id for camera in missing]))
                    .order_by(Emission.camera_id, Emission.timestamp.desc())
                    .distinct(Emission.camera_id)
                )
                fallback_by_database_id = {
                    emission.camera_id: emission
                    for emission in fallback_result.scalars().all()
                }

            for camera in cameras:
                payload = cached.get(camera.camera_id)
                if payload is None:
                    emission = fallback_by_database_id.get(camera.id)
                    if emission is None:
                        continue
                    payload = _legacy_emission_payload(camera.camera_id, emission)
                await websocket.send_text(json.dumps(payload))

            try:
                segment_result = await db.execute(select(RoadSegment).where(RoadSegment.road_segment_id.is_not(None)))
                segment_ids = [segment.road_segment_id for segment in segment_result.scalars().all()]
                segment_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                try:
                    segment_store = __import__("app.services.segment_latest_state", fromlist=["SegmentLatestStateStore"]).SegmentLatestStateStore(segment_client)
                    for segment_id in segment_ids:
                        state = await segment_client.get(segment_store.key_for(segment_id))
                        if state:
                            await websocket.send_text(json.dumps({"type": "segment_update", "segment_id": segment_id, "data": json.loads(state)}))
                finally:
                    await segment_client.aclose()
            except Exception:
                logger.warning("segment_latest_state_unavailable", exc_info=True)

    except Exception as e:
        logger.error(f"send_initial_state failed: {e}")


def _legacy_emission_payload(camera_id: str, emission: Emission) -> dict:
    payload = {
        "camera_id": camera_id,
        "timestamp": emission.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "car": emission.car,
        "motorcycle": emission.motorcycle,
        "bus": emission.bus,
        "truck": emission.truck,
        "total_tsp_g_per_min": emission.total_tsp_g_per_min,
        "total_tsp_kg_per_hr": emission.total_tsp_kg_per_hr,
        "total_nox_g_per_min": emission.total_nox_g_per_min,
        "total_nox_kg_per_hr": emission.total_nox_kg_per_hr,
        "total_so2_g_per_min": emission.total_so2_g_per_min,
        "total_so2_kg_per_hr": emission.total_so2_kg_per_hr,
        "total_hc_g_per_min": emission.total_hc_g_per_min,
        "total_hc_kg_per_hr": emission.total_hc_kg_per_hr,
        "total_co_g_per_min": emission.total_co_g_per_min,
        "total_co_kg_per_hr": emission.total_co_kg_per_hr,
        "total_co2_g_per_min": emission.total_co2_g_per_min,
        "total_co2_kg_per_hr": emission.total_co2_kg_per_hr,
        "total_ch4_g_per_min": emission.total_ch4_g_per_min,
        "total_ch4_kg_per_hr": emission.total_ch4_kg_per_hr,
        "total_n2o_g_per_min": emission.total_n2o_g_per_min,
        "total_n2o_kg_per_hr": emission.total_n2o_kg_per_hr,
        "cycle_duration_s": emission.cycle_duration_s,
    }
    return add_freshness(
        payload,
        observed_at=emission.timestamp,
        now=datetime.now(timezone.utc),
        policy=FreshnessPolicy.from_settings(settings),
    )


# ------------------------------------------------------------------
# WebSocket route
# ------------------------------------------------------------------

@router.websocket("/ws/emissions")
async def websocket_emissions(websocket: WebSocket):
    await manager.connect(websocket)

    # Send latest data immediately so client doesn't wait for next worker cycle
    await send_initial_state(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ------------------------------------------------------------------
# Redis subscriber — fans out compact latest-state payloads from the worker.
# The channel intentionally carries no frames, bounding boxes, or raw YOLO data.
# ------------------------------------------------------------------

async def redis_subscriber():
    logger.info("Redis subscriber starting...")

    while True:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            pubsub = client.pubsub()
            await pubsub.psubscribe("emissions:*")
            logger.info("Subscribed to latest emission pattern: emissions:*")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    data = message["data"]
                    await manager.broadcast(data)

        except Exception as e:
            logger.error(f"Redis subscriber error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)
        finally:
            try:
                await client.aclose()
            except Exception:
                pass
