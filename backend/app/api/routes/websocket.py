import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Send message to all connected clients. Remove stale connections silently."""
        stale = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                stale.add(connection)
        self.active_connections -= stale

manager = ConnectionManager()

# WebSocket Endpoint
@router.websocket("/ws/emissions")
async def websocket_emissions(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; we don't expect messages from clients
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Redis Subscriber
async def redis_subscriber():
    """
    Listens to Redis pub/sub pattern 'emissions:*'.
    Forwards every message to all connected WebSocket clients.
    Runs forever as a background task.
    """
    logger.info("Starting Redis subscriber...")
    
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