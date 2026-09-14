import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.routes import cameras, emissions, segment_emissions, spatial_layers, analytics_emissions, activity_grid, bangjo
from app.api.routes.websocket import router as websocket_router, redis_subscriber
from app.core.config import settings
from app.observability.logging import configure_logging
from app.observability.http import MetricsMiddleware
from app.observability.metrics import start_exporter
from app.observability.browser import router as telemetry_router

configure_logging()
 
app = FastAPI(
    title="EcoTraffic GIS",
    description="Real-time vehicle carbon emission monitoring for Yogyakarta",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------
# CORS - allow the React frontend (localhost:3000) to call the API
# ------------------------------------------------------------------
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    expose_headers=["X-Request-ID"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
app.include_router(telemetry_router)
app.include_router(cameras.router)
app.include_router(emissions.router)
app.include_router(analytics_emissions.router)
app.include_router(segment_emissions.router)
app.include_router(spatial_layers.router)
app.include_router(activity_grid.router)
app.include_router(bangjo.router)
app.include_router(websocket_router)

_background_tasks = set()

@app.on_event("startup")
async def startup_event():
    start_exporter()
    task = asyncio.create_task(redis_subscriber())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

@app.get("/health")
async def health():
    """Quick health check - used by Docker and monitoring."""
    return {"status": "ok", "debug": settings.DEBUG}
