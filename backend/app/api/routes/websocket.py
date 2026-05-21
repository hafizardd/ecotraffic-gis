import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_session_factory
from app.models.camera import Camera
from app.models.emission import Emission

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
    On new client connect, immediately send the latest emission row
    for each active camera. Fixes the blank state on page refresh.
    """
    try:
        factory = get_session_factory()
        async with factory() as db:
            cam_result = await db.execute(
                select(Camera).where(Camera.is_active == True)  # noqa: E712
            )
            cameras = cam_result.scalars().all()

            for camera in cameras:
                result = await db.execute(
                    select(Emission)
                    .where(Emission.camera_id == camera.id)
                    .order_by(Emission.timestamp.desc())
                    .limit(1)
                )
                emission = result.scalar_one_or_none()

                if emission:
                    payload = {
                        "camera_id": camera.camera_id,
                        "timestamp": emission.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "car": emission.car,
                        "motorcycle": emission.motorcycle,
                        "bus": emission.bus,
                        "truck": emission.truck,
                        "total_co_g_per_min": emission.total_co_g_per_min,
                        "total_co_kg_per_hr": emission.total_co_kg_per_hr,
                        "total_nox_g_per_min": emission.total_nox_g_per_min,
                        "total_nox_kg_per_hr": emission.total_nox_kg_per_hr,
                        "total_pm_g_per_min": emission.total_pm_g_per_min,
                        "total_pm_kg_per_hr": emission.total_pm_kg_per_hr,
                        "total_nmvoc_g_per_min": emission.total_nmvoc_g_per_min,
                        "total_nmvoc_kg_per_hr": emission.total_nmvoc_kg_per_hr,
                        "cycle_duration_s": emission.cycle_duration_s,
                    }
                    await websocket.send_text(json.dumps(payload))

    except Exception as e:
        logger.error(f"send_initial_state failed: {e}")


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
# Redis subscriber — runs as background task on app startup
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
            logger.info("Subscribed to Redis pattern: emissions:*")

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