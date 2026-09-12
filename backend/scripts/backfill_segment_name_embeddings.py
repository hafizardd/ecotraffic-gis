"""Backfill precomputed road-segment name embeddings for Bang Jo resolution.

Idempotent: only re-embeds name groups whose ``content_hash`` changed. Run once
after the migration, and again whenever road-segment names or the curated alias
map change.
"""

import hashlib
import logging

import httpx
from sqlalchemy import select

from app.api.routes.bangjo import _ALIAS_MAP, _normalize_name
from app.core.config import settings
from app.core.database import get_sync_db
from app.models.road_segment import RoadSegment
from app.models.segment_name_embedding import SegmentNameEmbedding

logger = logging.getLogger(__name__)


def _embed(text: str) -> list[float]:
    response = httpx.post(
        settings.BANGJO_EMBEDDINGS_URL,
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": settings.BANGJO_EMBEDDING_MODEL, "input": text},
        timeout=settings.BANGJO_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def backfill() -> dict[str, int]:
    if not settings.OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY is required to backfill embeddings")

    counts = {"groups": 0, "embedded": 0, "skipped": 0, "failed": 0}
    with get_sync_db() as db:
        groups: dict[str, dict] = {}
        for rid, name in db.execute(select(RoadSegment.road_segment_id, RoadSegment.name)).all():
            key = _normalize_name(name)
            if not key:
                continue
            group = groups.setdefault(key, {"display_name": name, "ids": []})
            group["ids"].append(rid)

        existing = {row.name_key: row for row in db.execute(select(SegmentNameEmbedding)).scalars()}
        for key, group in groups.items():
            counts["groups"] += 1
            aliases = [alias for alias, canonical in _ALIAS_MAP.items() if canonical == key]
            content = " ".join([group["display_name"], *aliases]).strip()
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            row = existing.get(key)
            if row is not None and row.content_hash == content_hash:
                counts["skipped"] += 1
                continue
            try:
                vector = _embed(content)
            except Exception:
                logger.exception("backfill_segment_name_embedding_failed", extra={"name_key": key})
                counts["failed"] += 1
                continue
            if row is None:
                row = SegmentNameEmbedding(
                    name_key=key, display_name=group["display_name"], road_segment_ids=[],
                    embedding=[], model=settings.BANGJO_EMBEDDING_MODEL, dim=len(vector),
                    content_hash=content_hash,
                )
                db.add(row)
            row.display_name = group["display_name"]
            row.road_segment_ids = group["ids"]
            row.embedding = vector
            row.model = settings.BANGJO_EMBEDDING_MODEL
            row.dim = len(vector)
            row.content_hash = content_hash
            db.commit()
            counts["embedded"] += 1

    print(counts)
    return counts


if __name__ == "__main__":
    backfill()
