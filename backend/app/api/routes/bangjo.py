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
    "Untuk pertanyaan intervensi koridor, pilih tepat satu berdasarkan context: "
    "coverage_gap=true -> tambah halte baru; weak_stop_count>0 -> perbaiki halte yang ada; "
    "activity_class 'Sangat Tinggi'/'Tinggi' dengan halte memadai -> tambah frekuensi layanan (armada). "
    "Sebut alasan dari field context, jangan mengarang. "
    "Field hourly_series berisi jam REPLAY prakomputasi; jika is_interpolated=true, "
    "sebut jam itu sebagai perkiraan/hasil interpolasi, bukan pengamatan pasti. "
    "Keluarkan HANYA objek JSON, tanpa pagar markdown dan tanpa penjelasan tambahan. "
    "Balas dengan JSON valid berbentuk: "
    '{"summary": str, "drivers": [str], "asi_category": str, "recommendation": str, "evidence": [str]}.'
)

CORRECTIVE_PROMPT = "Balas ulang HANYA dengan objek JSON valid sesuai instruksi, tanpa teks lain."

CLASS_ASI = {
    "Sangat Tinggi": "Avoid + Shift + Improve", "Tinggi": "Shift + Improve",
    "Sedang": "Improve", "Rendah": "Improve", "Sangat Rendah": "Improve",
}

HINT_PRIORITY = ("add_new_stop", "improve_existing_stop", "increase_frequency")
INTERVENTION_TEXT = {
    "add_new_stop": "tambah halte baru di segmen ini",
    "improve_existing_stop": "tingkatkan fasilitas/lingkungan halte yang ada",
    "increase_frequency": "tambah frekuensi layanan (jumlah armada)",
}


class HistoryTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    road_segment_id: str | None = None
    history: list[HistoryTurn] = Field(default_factory=list)


def _fallback_answer(context: dict, message: str, reason: str = "llm_error") -> dict:
    segment = context["segment"]
    activity = context["activity_potential"]
    stops = context["bus_stops"]
    activity_class = segment.get("activity_class")
    evidence = []
    if segment.get("activity_score") is not None:
        evidence.append(f"activity_score={round(segment['activity_score'], 3)}")
    if activity_class:
        evidence.append(f"klasifikasi_potensi={activity_class}")
    if activity.get("avg_skor_total_ahp") is not None:
        evidence.append(f"avg_skor_total_ahp={activity['avg_skor_total_ahp']}")
    if stops:
        evidence.append(f"halte dalam 500 m={len(stops)}")
    evidence.append(f"coverage_gap={context['coverage_gap']}")
    stop_assessment = context.get("stop_assessment") or {}
    if stop_assessment.get("weak_stop_count"):
        evidence.append(f"halte_kelas_rendah={stop_assessment['weak_stop_count']}")
    if stop_assessment.get("avg_ahp_total_score") is not None:
        evidence.append(f"avg_ahp_total_score_halte={stop_assessment['avg_ahp_total_score']}")
    chunk_count = segment.get("chunk_count") or 1
    if chunk_count > 1:
        evidence.append(f"segmen_digabung={chunk_count}")
    label = f"{segment['name']} ({chunk_count} segmen)" if chunk_count > 1 else f"{segment['name']} ({segment['road_segment_id']})"
    dominant = ", ".join(item["category"] for item in activity.get("dominant_poi_categories", [])) or "tidak tersedia"
    hint_phrase = INTERVENTION_TEXT.get(context.get("intervention_hint"))
    if hint_phrase:
        recommendation = f"Rekomendasi intervensi koridor ini: {hint_phrase}."
    elif activity_class:
        recommendation = "Fokuskan intervensi pada koridor ini; lengkapi data segmen bila potensi belum tersedia."
    else:
        recommendation = "Data potensi koridor belum tersedia, jadi rekomendasi spesifik belum dapat dibuat."
    return {
        "summary": (
            f"Koridor {label} memiliki potensi aktivitas "
            f"{activity_class or 'belum tersedia'}. Potensi aktivitas sekitar didominasi {dominant}."
        ),
        "drivers": [
            f"Potensi aktivitas rata-rata: {activity.get('avg_skor_total_ahp', 'tidak tersedia')}",
            f"Klasifikasi potensi: {', '.join(activity.get('klasifikasi_potensi') or []) or 'tidak tersedia'}",
        ],
        "asi_category": CLASS_ASI.get(activity_class, "Improve"),
        "recommendation": recommendation,
        "evidence": evidence,
        "source": "fallback",
        "fallback_reason": reason,
    }


def _normalize_name(name: str) -> str:
    text = re.sub(r"\b(?:jl|jln)\.?\s+", "jalan ", (name or "").casefold())
    return re.sub(r"\s+", " ", text).strip()


def _candidate_list(groups: list[list[dict]]) -> list[dict]:
    return [
        {"road_segment_id": members[0]["road_segment_id"], "name": members[0]["name"], "count": len(members)}
        for members in groups
    ]


async def _resolve_segment(db: AsyncSession, message: str) -> tuple[list[str] | None, list[dict]]:
    rows = (await db.execute(select(RoadSegment.road_segment_id, RoadSegment.name))).all()
    lower = _normalize_name(message)
    groups: dict[str, list[dict]] = {}
    for rid, name in rows:
        key = _normalize_name(name)
        if key:
            groups.setdefault(key, []).append({"road_segment_id": rid, "name": name})
    named = [members for key, members in groups.items() if key in lower or (lower and lower in key)]
    if len(named) == 1:
        return [member["road_segment_id"] for member in named[0]], []
    if len(named) > 1:
        return None, _candidate_list(named)
    tokens = {token for token in re.findall(r"[a-z0-9]+", lower) if len(token) > 3}
    scored = sorted(
        ((len(tokens & set(re.findall(r"[a-z0-9]+", key))), members) for key, members in groups.items()),
        key=lambda item: item[0],
        reverse=True,
    )
    if scored and scored[0][0] >= 2:
        return [member["road_segment_id"] for member in scored[0][1]], []
    return None, _candidate_list([members for _, members in scored[:5]])


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
        return _fallback_answer(context, message, "no_api_key")
    turns = [{"role": turn.role, "content": turn.content} for turn in history if turn.role in ("user", "assistant")]
    turns.append({"role": "user", "content": f"Konteks:\n{json.dumps(context, ensure_ascii=False)}\n\nPertanyaan: {message}"})
    base = {"model": settings.BANGJO_MODEL, "max_tokens": settings.BANGJO_MAX_TOKENS}
    url = settings.BANGJO_BASE_URL
    headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    started = time.monotonic()

    async def call(client: httpx.AsyncClient, messages: list[dict], structured: bool) -> dict | None:
        body = {**base, "messages": messages, **({"response_format": {"type": "json_object"}} if structured else {})}
        response = await client.post(url, headers=headers, json=body)
        if structured and response.status_code in (400, 404, 422):
            return None
        response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        return {
            "raw": choice.get("message", {}).get("content") or "",
            "finish_reason": choice.get("finish_reason"),
            "usage": data.get("usage") or {},
            "structured": structured,
        }

    def diagnostics(result: dict | None, reason: str | None = None) -> dict:
        extra = {
            "model": settings.BANGJO_MODEL,
            "structured": result.get("structured") if result else None,
            "finish_reason": result.get("finish_reason") if result else None,
            "usage": result.get("usage") if result else None,
            "raw_length": len(result["raw"]) if result else 0,
            "raw_preview": result["raw"][:500] if result else "",
        }
        if reason:
            extra["fallback_reason"] = reason
        if settings.BANGJO_DEBUG_RAW and result:
            extra["raw_text"] = result["raw"]
        return extra

    result: dict | None = None
    try:
        async with httpx.AsyncClient(timeout=settings.BANGJO_TIMEOUT_SECONDS) as client:
            conversation = [{"role": "system", "content": SYSTEM_PROMPT}, *turns]
            result = await call(client, conversation, structured=True)
            if result is None:
                result = await call(client, conversation, structured=False)
            try:
                parsed = _parse_answer(result["raw"])
            except ValueError:
                logger.warning("bangjo_llm_parse_failed", extra=diagnostics(result))
                retry = [*conversation, {"role": "assistant", "content": result["raw"]},
                         {"role": "user", "content": CORRECTIVE_PROMPT}]
                result = await call(client, retry, structured=False)
                parsed = _parse_answer(result["raw"])
        logger.info("bangjo_llm_call", extra={
            "source": "llm",
            "latency_s": round(time.monotonic() - started, 3),
            "input_tokens": result["usage"].get("prompt_tokens"),
            "output_tokens": result["usage"].get("completion_tokens"),
            "finish_reason": result["finish_reason"],
            "structured": result["structured"],
            "model": settings.BANGJO_MODEL,
        })
        return {**parsed, "source": "llm"}
    except httpx.TimeoutException:
        logger.exception("bangjo_llm_failed", extra=diagnostics(result, "timeout"))
        return _fallback_answer(context, message, "timeout")
    except httpx.HTTPStatusError:
        logger.exception("bangjo_llm_failed", extra=diagnostics(result, "http_error"))
        return _fallback_answer(context, message, "http_error")
    except ValueError:
        logger.warning("bangjo_llm_failed", extra=diagnostics(result, "parse_error"))
        return _fallback_answer(context, message, "parse_error")
    except Exception:
        logger.exception("bangjo_llm_failed", extra=diagnostics(result, "llm_error"))
        return _fallback_answer(context, message, "llm_error")


def _merge_hourly_series(contexts: list[dict]) -> list[dict]:
    """Sum each chunk's REPLAY hours; an hour is interpolated if any chunk is."""
    merged: dict[str, dict] = {}
    for context in contexts:
        for point in context.get("hourly_series") or []:
            hour = point["hour"]
            current = merged.get(hour)
            if current is None:
                merged[hour] = {
                    "hour": hour,
                    "emissions_kg_h": dict(point.get("emissions_kg_h") or {}),
                    "volume_per_hour": dict(point.get("volume_per_hour") or {}),
                    "is_interpolated": bool(point.get("is_interpolated")),
                    "interpolation_method": point.get("interpolation_method"),
                }
                continue
            emissions = current["emissions_kg_h"]
            for pollutant, value in (point.get("emissions_kg_h") or {}).items():
                if value is not None:
                    emissions[pollutant] = (emissions.get(pollutant) or 0) + value
            volume = current["volume_per_hour"]
            for category, value in (point.get("volume_per_hour") or {}).items():
                if value is not None:
                    volume[category] = (volume.get(category) or 0) + value
            current["is_interpolated"] = current["is_interpolated"] or bool(point.get("is_interpolated"))
            if point.get("interpolation_method") and not current["interpolation_method"]:
                current["interpolation_method"] = point["interpolation_method"]
    return [merged[hour] for hour in sorted(merged)]


def _merge_contexts(contexts: list[dict]) -> dict:
    """Aggregate same-name road chunks into one corridor context."""
    segments = [context["segment"] for context in contexts]
    potentials = [context["activity_potential"] for context in contexts]
    primary = max(
        segments,
        key=lambda segment: segment.get("activity_score") if segment.get("activity_score") is not None else -1,
    )
    totals: dict[str, float] = {}
    for segment in segments:
        for pollutant, value in (segment.get("pollutant_totals") or {}).items():
            if isinstance(value, (int, float)):
                totals[pollutant] = totals.get(pollutant, 0) + value
    poi: dict[str, int] = {}
    for potential in potentials:
        for item in potential.get("dominant_poi_categories") or []:
            poi[item["category"]] = poi.get(item["category"], 0) + int(item["count"])
    averages = [value for value in (p.get("avg_skor_total_ahp") for p in potentials) if value is not None]
    stops: dict[str, dict] = {}
    for context in contexts:
        for stop in context["bus_stops"]:
            current = stops.get(stop["source_id"])
            distance = stop.get("distance_to_segment_m")
            if current is None or (distance or float("inf")) < (current.get("distance_to_segment_m") or float("inf")):
                stops[stop["source_id"]] = stop
    observed = [segment["observed_at"] for segment in segments if segment.get("observed_at")]
    stop_assessments = [context.get("stop_assessment") or {} for context in contexts]
    class_counts: dict[str, int] = {}
    for assessment in stop_assessments:
        for label, count in (assessment.get("class_counts") or {}).items():
            class_counts[label] = class_counts.get(label, 0) + int(count)
    mins = [a["min_ahp_total_score"] for a in stop_assessments if a.get("min_ahp_total_score") is not None]
    avgs = [a["avg_ahp_total_score"] for a in stop_assessments if a.get("avg_ahp_total_score") is not None]
    hints = [context.get("intervention_hint") for context in contexts if context.get("intervention_hint")]
    return {
        "generated_at": max(context["generated_at"] for context in contexts),
        "segment": {
            "road_segment_id": primary["road_segment_id"],
            "road_segment_ids": [segment["road_segment_id"] for segment in segments],
            "chunk_count": len(contexts),
            "name": primary["name"],
            "length_km": round(sum(segment.get("length_km") or 0 for segment in segments), 3),
            "activity_class": primary.get("activity_class"),
            "activity_score": primary.get("activity_score"),
            "pollutant_totals": totals or None,
            "data_source": primary.get("data_source"),
            "observed_at": max(observed) if observed else None,
        },
        "activity_potential": {
            "hex_count": sum(p.get("hex_count") or 0 for p in potentials),
            "hex_ids": [hex_id for p in potentials for hex_id in (p.get("hex_ids") or [])],
            "avg_skor_total_ahp": round(sum(averages) / len(averages), 4) if averages else None,
            "max_skor_total_ahp": max(
                (p["max_skor_total_ahp"] for p in potentials if p.get("max_skor_total_ahp") is not None), default=None
            ),
            "klasifikasi_potensi": sorted({c for p in potentials for c in (p.get("klasifikasi_potensi") or [])}) or None,
            "dominant_poi_categories": [
                {"category": category, "count": count}
                for category, count in sorted(poi.items(), key=lambda item: item[1], reverse=True)
            ],
        },
        "bus_stops": list(stops.values()),
        "stop_assessment": {
            "count": sum(a.get("count") or 0 for a in stop_assessments),
            "scored_count": sum(a.get("scored_count") or 0 for a in stop_assessments),
            "class_counts": class_counts,
            "weak_stop_count": sum(a.get("weak_stop_count") or 0 for a in stop_assessments),
            "min_ahp_total_score": min(mins) if mins else None,
            "avg_ahp_total_score": round(sum(avgs) / len(avgs), 4) if avgs else None,
        },
        "coverage_gap": any(context["coverage_gap"] for context in contexts),
        "intervention_hint": next((hint for hint in HINT_PRIORITY if hint in hints), None),
        "hourly_series": _merge_hourly_series(contexts),
    }


@router.post("/bangjo")
async def bangjo_chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    segment_ids = [payload.road_segment_id] if payload.road_segment_id else None
    if not segment_ids:
        segment_ids, candidates = await _resolve_segment(db, payload.message)
        if not segment_ids:
            return {"needs_selection": True, "candidates": candidates, "answer": None, "context_label": None}
    contexts = [context for context in [await build_context(db, sid) for sid in segment_ids] if context]
    if not contexts:
        return {"needs_selection": True, "candidates": [], "answer": None, "context_label": None,
                "detail": f"Segmen '{segment_ids[0]}' tidak ditemukan."}
    context = _merge_contexts(contexts)
    answer = await _ask_llm(payload.message, context, payload.history)
    chunk_count = context["segment"]["chunk_count"]
    label = (f"{context['segment']['name']} ({chunk_count} segmen)" if chunk_count > 1
             else f"{context['segment']['name']} ({segment_ids[0]})")
    return {"needs_selection": False, "answer": answer, "context_label": label}
