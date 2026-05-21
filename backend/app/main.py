import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.routes import cameras, emissions
from app.api.routes.websocket import router as websocket_router, redis_subscriber
from app.core.config import settings
 
app = FastAPI(
    title="EcoTraffic GIS",
    description="Real-time vehicle carbon emission monitoring for Yogyakarta",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------
# CORS — allow the React frontend (localhost:3000) to call the API
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
app.include_router(cameras.router)
app.include_router(emissions.router)
app.include_router(websocket_router)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())

@app.get("/health")
async def health():
    """Quick health check — used by Docker and monitoring."""
    return {"status": "ok", "debug": settings.DEBUG}