"""Bounded, best-effort client telemetry. Never trusted for billing/security decisions."""
import json
import os
import time
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from app.observability.metrics import BROWSER_EVENTS, BROWSER_TIME

router = APIRouter()
NAMES = Literal['fetch_headers', 'fetch_body', 'video_load_event', 'video_error', 'video_loading_timeout', 'page_load', 'js_error', 'unhandled_rejection']
ROUTES = Literal['cameras', 'segments', 'emissions', 'spatial', 'analytics', 'chat', 'other', 'page', 'video']


class BrowserEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: NAMES
    route: ROUTES
    outcome: Literal['ok', 'error', 'aborted', 'timeout']
    duration_ms: float = Field(ge=0, le=3600000, allow_inf_nan=False)


class Batch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    events: list[BrowserEvent] = Field(min_length=1, max_length=20)


_tokens = 60.0
_updated = time.monotonic()


@router.post('/api/telemetry', include_in_schema=False)
async def telemetry(request: Request):
    global _tokens, _updated
    if os.getenv('BROWSER_TELEMETRY_ENABLED', 'false').lower() != 'true':
        return Response(status_code=204)
    origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    if request.headers.get('origin') not in origins:
        return Response(status_code=403)
    # Per-process aggregate cap; ingress should additionally enforce a per-IP limit.
    now = time.monotonic()
    _tokens = min(60, _tokens + (now - _updated) * 10)
    _updated = now
    if _tokens < 1:
        return Response(status_code=429)
    _tokens -= 1
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 8192:
            return Response(status_code=413)
    try:
        batch = Batch.model_validate(json.loads(payload))
    except (ValueError, ValidationError):
        return Response(status_code=422)
    for event in batch.events:
        labels = (event.name, event.route, event.outcome)
        BROWSER_EVENTS.labels(*labels).inc()
        BROWSER_TIME.labels(*labels).observe(event.duration_ms / 1000)
    return Response(status_code=204)
