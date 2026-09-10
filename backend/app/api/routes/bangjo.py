"""Bang Jo: evidence-grounded assistant over segment + hex + bus-stop context.

The LLM narrates a context object assembled from real queries; it is never
asked to recall or invent values. Any LLM failure degrades to a deterministic
summary built from the same context (never a 500).
"""

import json
import logging
import re
import time

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.road_segment import RoadSegment
from app.services.bangjo_context import build_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_PROMPT = (
    "Anda adalah Bang Jo, asisten WebGIS EcoTraffic Yogyakarta. "
    "Jawab HANYA berdasarkan objek konteks JSON yang diberikan. "
    "JANGAN menyebut angka yang tidak ada di konteks. Jika data tidak tersedia, katakan tidak tersedia. "
    "Gunakan kerangka ASI: Avoid (hindari), Shift (alihkan), Improve (perbaiki). "
    "Keluarkan HANYA objek JSON, tanpa pagar markdown dan tanpa penjelasan tambahan. "
    "Balas dengan JSON valid berbentuk: "
    '{"summary": str, "drivers": [str], "asi_category": str, "recommendation": str, "evidence": [str]}.'
)

PRIORITY_ASI = {
    "Critical": "Avoid + Shift + Improve", "Very High": "Shift + Improve",
    "High": "Improve", "Moderate": "Improve", "Low": "Improve",
}


class HistoryTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    road_segment_id: str | None = None
    history: list[HistoryTurn] = Field(default_factory=list)


def _fallback_answer(context: dict, message: str) -> dict:
    segment = context["segment"]
    activity = context["activity_potential"]
    stops = context["bus_stops"]
    priority = segment.get("priority")
    evidence = []
    if segment.get("decision_score") is not None:
        evidence.append(f"decision_score={round(segment['decision_score'], 3)}")
    if priority:
        evidence.append(f"priority={priority}")
    if activity.get("avg_skor_total_ahp") is not None:
        evidence.append(f"avg_skor_total_ahp={activity['avg_skor_total_ahp']}")
    if stops:
        evidence.append(f"halte dalam 500 m={len(stops)}")
    evidence.append(f"coverage_gap={context['coverage_gap']}")
    dominant = ", ".join(item["category"] for item in activity.get("dominant_poi_categories", [])) or "tidak tersedia"
    return {
        "summary": (
            f"Koridor {segment['name']} ({segment['road_segment_id']}) memiliki prioritas "
            f"{priority or 'belum dinilai'}. Potensi aktivitas sekitar didominasi {dominant}."
        ),
        "drivers": [
            f"Potensi aktivitas rata-rata: {activity.get('avg_skor_total_ahp', 'tidak tersedia')}",
            f"Klasifikasi potensi: {', '.join(activity.get('klasifikasi_potensi') or []) or 'tidak tersedia'}",
        ],
        "asi_category": PRIORITY_ASI.get(priority, "Improve"),
        "recommendation": (
            "Fokuskan intervensi pada koridor ini; lengkapi data segmen bila skor belum tersedia."
            if priority else "Data skor koridor belum tersedia, jadi rekomendasi spesifik belum dapat dibuat."
        ),
        "evidence": evidence,
        "source": "fallback",
    }


async def _resolve_segment(db: AsyncSession, message: str) -> tuple[str | None, list[dict]]:
    rows = (await db.execute(select(RoadSegment.road_segment_id, RoadSegment.name))).all()
    lower = message.casefold()
    named = [{"road_segment_id": rid, "name": name} for rid, name in rows if name and name.casefold() in lower]
    if len(named) == 1:
        return named[0]["road_segment_id"], []
    if len(named) > 1:
        return None, named
    tokens = {token for token in re.findall(r"[a-z0-9]+", lower) if len(token) > 3}
    scored = sorted(
        (
            (len(tokens & set(re.findall(r"[a-z0-9]+", (name or "").casefold()))), rid, name)
            for rid, name in rows
        ),
        reverse=True,
    )
    if scored and scored[0][0] >= 2:
        return scored[0][1], []
    return None, [{"road_segment_id": rid, "name": name} for rid, name in rows[:20]]


_STRING_KEYS = ("summary", "asi_category", "recommendation")
_LIST_KEYS = ("drivers", "evidence")
_SMART_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def _extract_json(text: str) -> str | None:
    stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end == -1:
        return None
    return stripped[start:end + 1]


def _repair_json(candidate: str) -> str:
    text = candidate.translate(_SMART_QUOTES)
    text = re.sub(r"//[^\n\r]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _coerce(value, *, is_list: bool):
    if is_list:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if value else []
    return "" if value is None else str(value).strip()


def _normalize_answer(parsed: dict) -> dict:
    answer = {key: _coerce(parsed.get(key), is_list=False) for key in _STRING_KEYS}
    for key in _LIST_KEYS:
        answer[key] = _coerce(parsed.get(key), is_list=True)
    if not answer["summary"]:
        answer["summary"] = answer["recommendation"]
    if not answer["summary"]:
        raise ValueError("LLM answer missing summary")
    return answer


def _string_field(text: str, key: str) -> str:
    match = re.search(
        rf'["\']?{re.escape(key)}["\']?\s*[:=]\s*(?:"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|([^,\n\r}}]+))',
        text, re.IGNORECASE,
    )
    if not match:
        return ""
    raw = next((group for group in match.groups() if group is not None), "")
    return raw.replace('\\"', '"').replace("\\n", " ").strip().strip("\"'").strip()


def _list_field(text: str, key: str) -> list[str]:
    match = re.search(rf'["\']?{re.escape(key)}["\']?\s*[:=]\s*\[([^\]]*)\]', text, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    items = []
    for double, single in re.findall(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'', match.group(1)):
        value = (double or single).replace('\\"', '"').strip()
        if value:
            items.append(value)
    return items


def _regex_answer(text: str) -> dict:
    answer = {key: _string_field(text, key) for key in _STRING_KEYS}
    for key in _LIST_KEYS:
        answer[key] = _list_field(text, key)
    if not answer["summary"]:
        raise ValueError("LLM response contained no usable summary")
    return answer


def _parse_answer(text: str) -> dict:
    """Three-stage parse: strict JSON, repaired JSON, then tolerant field extraction."""
    candidate = _extract_json(text)
    if candidate is not None:
        for raw in (candidate, _repair_json(candidate)):
            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if isinstance(parsed, dict):
                try:
                    return _normalize_answer(parsed)
                except ValueError:
                    break
    return _regex_answer(text)


async def _ask_llm(message: str, context: dict, history: list[HistoryTurn]) -> dict:
    if not settings.OPENROUTER_API_KEY:
        return _fallback_answer(context, message)
    turns = [{"role": turn.role, "content": turn.content} for turn in history if turn.role in ("user", "assistant")]
    turns.append({"role": "user", "content": f"Konteks:\n{json.dumps(context, ensure_ascii=False)}\n\nPertanyaan: {message}"})
    payload = {
        "model": settings.BANGJO_MODEL, "max_tokens": settings.BANGJO_MAX_TOKENS,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *turns],
    }
    started = time.monotonic()
    raw_text = ""
    try:
        async with httpx.AsyncClient(timeout=settings.BANGJO_TIMEOUT_SECONDS) as client:
            for structured in (True, False):
                body = {**payload, **({"response_format": {"type": "json_object"}} if structured else {})}
                response = await client.post(
                    settings.BANGJO_BASE_URL,
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                    json=body,
                )
                if structured and response.status_code in (400, 404, 422):
                    continue
                response.raise_for_status()
                data = response.json()
                break
        raw_text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        parsed = _parse_answer(raw_text)
        logger.info("bangjo_llm_call", extra={
            "latency_s": round(time.monotonic() - started, 3),
            "input_tokens": (data.get("usage") or {}).get("prompt_tokens"),
            "output_tokens": (data.get("usage") or {}).get("completion_tokens"),
        })
        return {**parsed, "source": "llm"}
    except Exception:
        logger.exception("bangjo_llm_failed", extra={"raw_preview": raw_text[:500]})
        return _fallback_answer(context, message)


@router.post("/bangjo")
async def bangjo_chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    road_segment_id = payload.road_segment_id
    if not road_segment_id:
        road_segment_id, candidates = await _resolve_segment(db, payload.message)
        if not road_segment_id:
            return {"needs_selection": True, "candidates": candidates, "answer": None, "context_label": None}
    context = await build_context(db, road_segment_id)
    if context is None:
        return {"needs_selection": True, "candidates": [], "answer": None, "context_label": None,
                "detail": f"Segmen '{road_segment_id}' tidak ditemukan."}
    answer = await _ask_llm(payload.message, context, payload.history)
    return {
        "needs_selection": False, "answer": answer,
        "context_label": f"{context['segment']['name']} ({road_segment_id})",
    }
