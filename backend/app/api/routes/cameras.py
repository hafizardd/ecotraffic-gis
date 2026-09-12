import asyncio
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.camera import Camera
from app.services.data_freshness import FreshnessPolicy, classify_freshness
from app.schemas.camera import (
    CameraFeature,
    CameraFeatureCollection,
    CameraProperties,
    GeoJSONPoint,
)

router = APIRouter(prefix="/api/cameras", tags=["cameras"])

# On-demand snapshot cache (seconds). The tracker already publishes
# tracks:snapshot:{id} at ~10fps; this only covers tracker gaps.
ONDEMAND_SNAPSHOT_TTL_SECONDS = 15
# Filenames Wowza HLS may reference. Anything else is rejected (SSRF guard).
_LIVE_EXTENSIONS = ("m3u8", "ts", "m4s", "mp4", "key", "vtt")
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.(m3u8|ts|m4s|mp4|key|vtt)$")
_URI_ATTR = re.compile(r'URI="([^"]+)"')

_http_client: httpx.AsyncClient | None = None


def _live_cam_ids() -> list[str]:
    return [c.strip() for c in settings.TRACK_CAMS.split(",") if c.strip()]


def _is_live_cam(camera_id: str) -> bool:
    return camera_id in _live_cam_ids()


def _upstream_base(stream_url: str) -> str:
    return stream_url.rsplit("/", 1)[0]


def _safe_live_filename(name: str) -> str | None:
    base = urlparse(name).path.rsplit("/", 1)[-1]
    if not base or not _SAFE_FILENAME.match(base):
        return None
    ext = base.rsplit(".", 1)[-1].lower()
    if ext not in _LIVE_EXTENSIONS:
        return None
    return base


def _rewrite_playlist(text: str, camera_id: str) -> str:
    """Rewrite upstream segment URIs to proxied /live/ URLs (Referer+CORS fix)."""
    prefix = f"/api/cameras/{camera_id}/live/"
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        if stripped.startswith("#"):
            def _replace(m: "re.Match[str]") -> str:
                safe = _safe_live_filename(m.group(1))
                if safe is None:
                    return m.group(0)
                return f'URI="{prefix}{safe}"'
            out.append(_URI_ATTR.sub(_replace, line))
            continue
        safe = _safe_live_filename(stripped)
        out.append(f"{prefix}{safe}" if safe else line)
    return "\n".join(out) + "\n"


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            # Playlists are tiny (fast); segments are multi-MB over a slow
            # upstream link, so reads get a generous per-read timeout and
            # segments stream chunk-by-chunk instead of buffering.
            timeout=httpx.Timeout(60.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "EcoTrafficGIS/1.0"},
        )
    return _http_client


def _segment_media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "m3u8": "application/vnd.apple.mpegurl",
        "ts": "video/MP2T",
        "m4s": "video/mp4",
        "mp4": "video/mp4",
        "vtt": "text/vtt",
        "key": "application/octet-stream",
    }.get(ext, "application/octet-stream")


async def _get_live_source(camera_id: str, db: AsyncSession) -> tuple[str, str | None]:
    if not _is_live_cam(camera_id):
        raise HTTPException(status_code=403, detail=f"Live proxy not enabled for '{camera_id}'.")
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    if camera is None or not camera.is_active:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")
    return camera.stream_url, camera.referer


@router.get("", response_model=CameraFeatureCollection)
async def get_cameras(data_source: str | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Camera,
            text("ST_AsGeoJSON(cameras.location)::json as geojson")
        )
        .where(Camera.is_active == True)
        .where(Camera.data_source == data_source if data_source else True)
        .order_by(Camera.created_at)
    )
    rows = result.all()
    now = datetime.now(timezone.utc)

    features = []
    for camera, geojson in rows:
        coords = geojson["coordinates"]  # [longitude, latitude]
        features.append(
            CameraFeature(
                geometry=GeoJSONPoint(coordinates=coords),
                properties=_camera_properties(camera, now)
            )
        )

    return CameraFeatureCollection(features=features)


# Live routes before /{camera_id} so the generic route never shadows them.
@router.get("/{camera_id}/live/playlist.m3u8")
async def get_live_playlist(camera_id: str, db: AsyncSession = Depends(get_db)):
    """Proxied HLS playlist with Referer injection (browser can't set Referer)."""
    stream_url, referer = await _get_live_source(camera_id, db)
    headers = {"Referer": referer} if referer else {}
    try:
        resp = await _get_http_client().get(stream_url, headers=headers)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=f"Upstream stream unavailable for '{camera_id}'.")
    if resp.status_code != 200 or not resp.text:
        raise HTTPException(status_code=503, detail=f"Upstream stream unavailable for '{camera_id}'.")
    body = _rewrite_playlist(resp.text, camera_id)
    return Response(content=body, media_type="application/vnd.apple.mpegurl",
                    headers={"Cache-Control": "no-cache"})


@router.get("/{camera_id}/live/{filename}")
async def get_live_segment(camera_id: str, filename: str, db: AsyncSession = Depends(get_db)):
    """Proxied HLS segment/chunklist with Referer injection.

    Media segments stream chunk-by-chunk (first bytes flow immediately)
    because the upstream link is slow (~60KB/s for multi-MB segments).
    """
    safe = _safe_live_filename(filename)
    if safe is None:
        raise HTTPException(status_code=404, detail="Segment not found.")
    stream_url, referer = await _get_live_source(camera_id, db)
    upstream = f"{_upstream_base(stream_url)}/{safe}"
    headers = {"Referer": referer} if referer else {}
    media_type = _segment_media_type(safe)
    if safe.endswith(".m3u8"):
        # The master playlist is rewritten, but its child media playlist also
        # contains relative segment names and must be rewritten here.
        try:
            resp = await _get_http_client().get(upstream, headers=headers)
        except httpx.HTTPError:
            raise HTTPException(status_code=503, detail=f"Upstream segment unavailable for '{camera_id}'.")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code if resp.status_code in (403, 404) else 503,
                                detail="Upstream segment unavailable.")
        body = _rewrite_playlist(resp.text, camera_id)
        return Response(content=body, media_type=media_type,
                        headers={"Cache-Control": "no-cache"})

    async def _stream_upstream():
        try:
            async with _get_http_client().stream("GET", upstream, headers=headers) as resp:
                if resp.status_code != 200:
                    return
                async for chunk in resp.aiter_bytes(64 * 1024):
                    yield chunk
        except httpx.HTTPError:
            return

    return StreamingResponse(_stream_upstream(), media_type=media_type,
                             headers={"Cache-Control": "max-age=2"})


@router.get("/{camera_id}/tracked.mjpg")
async def get_tracked_stream(camera_id: str, db: AsyncSession = Depends(get_db)):
    """Annotated MJPEG stream: frames already contain boxes + track IDs.

    The tracking worker (one per camera, independent of viewers) writes the
    latest annotated JPEG to ``tracks:snapshot:{camera_id}``. This endpoint
    only polls that key - it never runs YOLO. Multiple clients share the
    same tracker.
    """
    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    if camera is None or not camera.is_active:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")

    interval = 1.0 / float(settings.STREAM_FPS)

    async def _generate():
        client = redis.Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=5, socket_timeout=5
        )
        try:
            last_payload: bytes | None = None
            while True:
                try:
                    payload = await asyncio.to_thread(
                        client.get, f"tracks:snapshot:{camera_id}"
                    )
                except Exception:
                    await asyncio.sleep(interval)
                    continue
                if payload is not None and payload != last_payload:
                    last_payload = bytes(payload)
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(last_payload)).encode() + b"\r\n"
                        b"\r\n" + last_payload + b"\r\n"
                    )
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            # Browser disconnected; tracker keeps running untouched.
            raise
        finally:
            try:
                client.close()
            except Exception:
                pass

    return StreamingResponse(
        _generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{camera_id}", response_model=CameraProperties)
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns a single camera by its slug (camera_id).
    """
    result = await db.execute(
        select(Camera).where(Camera.camera_id == camera_id)
    )
    camera = result.scalar_one_or_none()

    if camera is None:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")

    return _camera_properties(camera, datetime.now(timezone.utc))


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str, db: AsyncSession = Depends(get_db)):
    """Latest tracking JPEG, with on-demand ffmpeg fallback when tracker stalls.

    Primary: tracks:snapshot:{id} from tracking_worker. Fallback: single
    ffmpeg frame (mjpeg bytes, no OpenCV in API process), cached 15s under
    snapshot:ondemand:{id} so concurrent poster loads share one capture.
    """
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        try:
            payload = client.get(f"tracks:snapshot:{camera_id}")
            if payload is not None:
                return Response(content=bytes(payload), media_type="image/jpeg")
            cached = client.get(f"snapshot:ondemand:{camera_id}")
            if cached is not None:
                return Response(content=bytes(cached), media_type="image/jpeg")
        finally:
            try:
                client.close()
            except Exception:
                pass
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Snapshot store unavailable.")

    if not _is_live_cam(camera_id):
        raise HTTPException(status_code=404, detail=f"No tracking snapshot for '{camera_id}'.")

    result = await db.execute(select(Camera).where(Camera.camera_id == camera_id))
    camera = result.scalar_one_or_none()
    if camera is None or not camera.is_active:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")

    jpeg = await _capture_ondemand_jpeg(camera.stream_url, camera.referer)
    if jpeg is None:
        raise HTTPException(status_code=503, detail=f"Snapshot capture failed for '{camera_id}'.")
    try:
        cache_client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        try:
            cache_client.setex(f"snapshot:ondemand:{camera_id}", ONDEMAND_SNAPSHOT_TTL_SECONDS, jpeg)
        finally:
            try:
                cache_client.close()
            except Exception:
                pass
    except Exception:
        pass
    return Response(content=jpeg, media_type="image/jpeg")


async def _capture_ondemand_jpeg(stream_url: str, referer: str | None) -> bytes | None:
    """Single ffmpeg frame as mjpeg bytes (keeps API image free of OpenCV)."""
    timeout = int(settings.FRAME_FFMPEG_TIMEOUT_SECONDS)
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-rw_timeout", str(timeout * 1_000_000),
    ]
    if referer:
        command.extend(["-headers", f"Referer: {referer}\r\n"])
    command.extend(["-i", stream_url, "-frames:v", "1",
                    "-f", "image2", "-vcodec", "mjpeg", "-q:v", "3", "-"])
    try:
        completed = await asyncio.to_thread(
            subprocess.run, command, capture_output=True, timeout=timeout, check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0 or not completed.stdout:
        return None
    if len(completed.stdout) > int(settings.INFERENCE_FRAME_MAX_BYTES):
        return None
    return bytes(completed.stdout)


@router.get("/{camera_id}/tracks")
async def get_camera_tracks(camera_id: str):
    """Latest track payload + normalized ROI for the verification overlay."""
    from cv.rois import resolve, to_normalized

    if resolve(camera_id) is None:
        raise HTTPException(status_code=404, detail=f"No ROI configured for '{camera_id}'.")
    return {"camera_id": camera_id, "roi": to_normalized(camera_id)}


def _camera_properties(camera: Camera, now: datetime) -> CameraProperties:
    freshness = classify_freshness(
        camera.last_success_at,
        now=now,
        policy=FreshnessPolicy.from_settings(settings),
    )
    return CameraProperties(
        id=camera.id,
        name=camera.name,
        camera_id=camera.camera_id,
        stream_url=camera.stream_url,
        is_active=camera.is_active,
        data_source=camera.data_source,
        status=camera.status,
        failure_count=camera.failure_count,
        last_sample_at=camera.last_sample_at,
        last_success_at=camera.last_success_at,
        last_error_at=camera.last_error_at,
        freshness_status=freshness.status.value,
        data_age_seconds=freshness.age_seconds,
        created_at=camera.created_at,
    )
