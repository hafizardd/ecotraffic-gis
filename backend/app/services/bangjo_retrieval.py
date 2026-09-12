"""Entity-resolution retrieval for Bang Jo.

Phase 1 is embeddings only: precomputed vectors for road-segment name groups,
compared with cosine similarity in Python. The document-corpus RAG seam
(:func:`retrieve`) is reserved and returns ``[]`` until a corpus exists.

Every failure (disabled flag, no API key, HTTP error, missing table, empty
corpus, threshold miss) returns ``None``/``[]`` so resolution falls back to the
string matcher. This module never raises into the request path.
"""

import logging
import math
import time

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.models.segment_name_embedding import SegmentNameEmbedding

logger = logging.getLogger(__name__)

_DOC_CACHE: list[dict] = []
_DOC_CACHE_AT = 0.0
_DOC_CACHE_TTL_SECONDS = 60.0


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return -1.0
    return dot / (norm_a * norm_b)


async def load_document_vectors(db, force: bool = False) -> list[dict]:
    """Load the small name-vector corpus into an in-process cache."""
    global _DOC_CACHE, _DOC_CACHE_AT
    now = time.monotonic()
    if not force and _DOC_CACHE_AT and now - _DOC_CACHE_AT < _DOC_CACHE_TTL_SECONDS:
        return _DOC_CACHE
    try:
        rows = (
            await db.execute(
                select(
                    SegmentNameEmbedding.name_key,
                    SegmentNameEmbedding.display_name,
                    SegmentNameEmbedding.road_segment_ids,
                    SegmentNameEmbedding.embedding,
                )
            )
        ).all()
    except Exception:
        logger.warning("bangjo_embedding_load_failed", exc_info=True)
        return _DOC_CACHE
    _DOC_CACHE = [
        {
            "name_key": name_key,
            "display_name": display_name,
            "road_segment_ids": list(road_segment_ids or []),
            "embedding": list(embedding or []),
        }
        for name_key, display_name, road_segment_ids, embedding in rows
    ]
    _DOC_CACHE_AT = now
    return _DOC_CACHE


async def embed_text(text: str) -> list[float] | None:
    if not settings.OPENROUTER_API_KEY or not text:
        return None
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {"model": settings.BANGJO_EMBEDDING_MODEL, "input": text}
    try:
        async with httpx.AsyncClient(timeout=settings.BANGJO_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.BANGJO_EMBEDDINGS_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        vector = list((data.get("data") or [{}])[0].get("embedding") or [])
        return vector or None
    except Exception:
        logger.warning("bangjo_embedding_query_failed", exc_info=True)
        return None


async def resolve_by_embedding(db, query: str) -> list[str] | None:
    if not settings.BANGJO_EMBEDDINGS_ENABLED:
        return None
    documents = await load_document_vectors(db)
    if not documents:
        return None
    vector = await embed_text(query)
    if not vector:
        return None
    best, best_score = None, -1.0
    for document in documents:
        score = cosine(vector, document["embedding"])
        if score > best_score:
            best, best_score = document, score
    if best is None or best_score < settings.BANGJO_RESOLUTION_THRESHOLD:
        return None
    return list(best["road_segment_ids"])


def reset_document_cache() -> None:
    global _DOC_CACHE, _DOC_CACHE_AT
    _DOC_CACHE = []
    _DOC_CACHE_AT = 0.0


def retrieve(db, query: str, entity=None) -> list:
    """Reserved seam for unstructured-document RAG (no corpus exists yet)."""
    return []
