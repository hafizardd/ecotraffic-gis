"""Bang Jo: evidence-grounded assistant over segment + hex + bus-stop context.

The LLM narrates a context object assembled from real queries in natural
Indonesian markdown; it is never asked to recall or invent values. When the LLM
is unavailable or returns unusable prose, the route fails loudly with a
retryable error instead of substituting a deterministic answer.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.road_segment import RoadSegment
from app.models.spatial_sources import SurveyStopObservation
from app.services.bangjo_context import (
    activity_overview_payload,
    build_activity_overview_context,
    build_bus_stop_overview_context,
    build_context,
    build_hex_context,
    build_overview_context,
    build_stop_context,
    bus_stop_payload,
    overview_payload,
    segment_for_stop,
    segments_for_hex,
    verify_context_result,
)
from app.services.bangjo_guardrails import (
    NO_SCOPE_MATCH,
    _GREETING,
    DECLINE_MESSAGE,
    sanitize_history,
    screen_query,
)
from app.services.bangjo_project_knowledge import build_meta_context, is_meta_query
from app.services.bangjo_retrieval import resolve_by_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_PROMPT = (
    "Anda adalah Bang Jo, asisten WebGIS EcoTraffic Yogyakarta. "
    "Jawab berdasarkan objek konteks JSON yang diberikan; jangan mengarang angka di luar konteks. "
    "Jika sebuah dimensi memang tidak ada di konteks, katakan datanya belum tersedia pada konteks ini "
    "lalu sebutkan dimensi yang tersedia. "
    "Konteks bisa berbentuk (a) satu koridor pada field 'segment', atau (b) ringkasan seluruh koridor "
    "dengan scope='overview' (field ringkasan, emisi_tertinggi, emisi_terendah, butuh_intervensi, pita_emisi), "
    "atau (c) peringkat kualitas halte dengan scope='bus_stops' (field ringkasan, halte_terbaik, halte_terburuk; "
    "satuan skor 0-100 dan MAKIN TINGGI MAKIN BAIK), atau (d) satu halte pada field 'stop' (skor_total, aksesibilitas, "
    "kondisi, lingkungan, jumlah_fasilitas, jumlah_kerusakan) beserta koridor terdekatnya, "
    "atau (e) peringkat potensi aktivitas sel grid dengan scope='hex_activity' (field ringkasan, potensi_tertinggi, "
    "potensi_terendah; satuan skor 0-100 dan MAKIN TINGGI MAKIN TINGGI POTENSI AKTIVITAS). "
    "Untuk pertanyaan 'daerah dengan potensi aktivitas tertinggi/terendah', jawab dari ringkasan pada scope='hex_activity': "
    "sebut sel beserta koridor yang melintasinya dan poi_utama sebagai pemicu; jangan menyebut angka sel sebagai nama tempat. "
    "Daftar potensi_tertinggi/potensi_terendah hanya sebagian (lihat 'dipotong'); gunakan ringkasan untuk jawaban pasti. "
    "Jika konteks memuat 'displayed_hour_label', itu adalah jam/tanggal yang sedang dilihat pengguna pada peta; "
    "sebut waktu itu apa adanya saat menjelaskan sel grid, dan gunakan nilai hex_cell (skor_total_ahp, ranking, "
    "klasifikasi_potensi, data_status) sebagai nilai pada jam tersebut (field 'static' hanyalah snapshot offline). "
    "Jika konteks memuat data_mode='live', nilai hex_cell adalah pembacaan live TERBARU (bukan jam REPLAY tertentu); "
    "sebut sebagai data live dan JANGAN menyebut jam tampilan. "
    "Jika data_status='fallback', sebut nilainya perkiraan dari sel terdekat; jika is_interpolated=true, sebut hasil interpolasi. "
    "Jika konteks memuat penilaian kualitas halte ('stop' atau scope='bus_stops'), data itu TERSEDIA: jawab dari situ "
    "dan JANGAN pernah menyatakan penilaian kualitas halte tidak tersedia. "
    "Jika konteks berbentuk ringkasan: bandingkan total_emisi antar koridor; pakai "
    "ringkasan.tertinggi/ringkasan.median/ringkasan.terendah untuk pertanyaan tertinggi/normal/terendah; "
    "gunakan pita_emisi sebagai penentu 'tinggi'/'sedang'/'rendah' (JANGAN membuat ambang batas sendiri), "
    "dan hanya sebut koridor berlabel 'Tinggi' sebagai emisi tinggi. "
    "Untuk pertanyaan 'ruas jalan/koridor terbaik atau terburuk': 'terburuk' = emisi tertinggi "
    "(ringkasan.tertinggi) dan 'terbaik' = emisi terendah (ringkasan.terendah); jangan menukar keduanya. "
    "Daftar emisi_tertinggi/emisi_terendah hanya sebagian (lihat emisi_dipotong dan jumlah_tanpa_emisi); "
    "pakai ringkasan untuk jawaban pasti dan sebutkan bila ada koridor yang belum punya data emisi. "
    "Gunakan kerangka ASI: Avoid (hindari), Shift (alihkan), Improve (perbaiki). "
    "Untuk rekomendasi intervensi koridor, pilih tepat satu langkah berdasarkan konteks: "
    "kekosongan cakupan halte -> tambah halte baru; halte lemah -> perbaiki halte yang ada; "
    "kelas aktivitas 'Sangat Tinggi'/'Tinggi' dengan halte memadai -> tambah frekuensi layanan (armada). "
    "Untuk pertanyaan 'halte terbaik/terburuk', gunakan ringkasan.terbaik/terburuk dan halte_terbaik/halte_terburuk "
    "dari konteks; skor lebih tinggi = lebih baik; jangan membuat ambang batas atau metrik sendiri. "
    "Field hourly_series berisi jam REPLAY prakomputasi; jika is_interpolated=true, "
    "sebut jam itu sebagai perkiraan/hasil interpolasi, bukan pengamatan pasti. "
    "Jika hanya ada hourly_series_ringkasan (tanpa hourly_series), itu ringkasan jam; jangan mengarang "
    "angka per jam, dan tawarkan pengguna bertanya 'tren per jam' bila perlu rincian. "
    "Jika segment.is_estimated=true atau status_data='perkiraan', atau hex_cell.data_status='fallback', "
    "sebut nilai itu sebagai PERKIRAAN dari segmen/sel terdekat (sebut borrowed_from/fallback_from bila ada), "
    "bukan pengukuran. Jika segment.is_static=true, sebut datanya statis (profil 24 jam), bukan arus langsung. "
    "Jangan pernah menyebut perkiraan/data statis sebagai nilai terukur."
    "Jika konteks yang diberikan bukan objek yang ditanyakan (misalnya pengguna menyebut koridor/halte lain), "
    "sebut objek yang sedang dijawab dan arahkan pengguna ke objek itu. "
    "Jika konteks belum memuat data yang diminta, sebutkan dimensi yang tersedia di konteks dan "
    "tawarkan pengguna menanyakannya secara spesifik. "
    "Jawab topik pada pertanyaan TERBARU; gunakan riwayat hanya untuk memahami rujukan seperti 'itu', 'yang tadi', "
    "atau 'lainnya', dan jangan lanjut membahas topik lama bila pertanyaan terbaru sudah berpindah objek. "
    "PENTING: tulis dalam Bahasa Indonesia manusia. JANGAN pernah menampilkan nama field atau kode teknis "
    "(misalnya yang mengandung garis bawah '_', atau kode seperti increase_frequency, add_new_stop, "
    "improve_existing_stop, coverage_gap, weak_stop_count). Terjemahkan: increase_frequency menjadi "
    "'tambah frekuensi layanan', add_new_stop menjadi 'tambah halte baru', improve_existing_stop menjadi "
    "'perbaiki halte yang ada'. "
    "Salin semua angka persis dari konteks; jangan membulatkan, menambah, atau mengarang angka/ambang batas. "
    "Balas memakai markdown ringan saja: teks tebal **teks**, daftar '- ' di awal baris, dan paragraf. "
    "Jangan pakai heading, tabel, tautan, blok kode, JSON, atau HTML mentah. "
    "Jangan pernah mengisi jawaban dengan kata 'str', '...', atau placeholder; tulis kalimat sebenarnya. "
    "Keluarkan HANYA jawaban markdown itu sendiri, tanpa kalimat pembuka atau penutup."
)

STYLE_INSTRUCTIONS = {
    "intervention": (
        "Susun jawaban dengan bagian berikut: **Ringkasan** (2-3 kalimat), **Pendorong** (daftar), "
        "**Rekomendasi ASI** (tepat satu langkah + alasan dari konteks), **Bukti** (daftar angka dari konteks)."
    ),
    "general": (
        "Jawab langsung dan ringkas (1-3 paragraf atau daftar pendek) sesuai pertanyaan. "
        "JANGAN memaksa bagian Ringkasan/Pendorong/Rekomendasi ASI/Bukti; pakai format itu hanya bila "
        "pengguna memang meminta rekomendasi intervensi."
    ),
}


def _system_prompt(style: str) -> str:
    return f"{SYSTEM_PROMPT}\n{STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS['general'])}"


CORRECTIVE_PROMPT = (
    "Jawaban sebelumnya tidak valid. Tulis ulang HANYA jawaban dalam Bahasa Indonesia alami "
    "berformat markdown ringan sesuai gaya yang diminta. "
    "Jangan keluarkan JSON, jangan pakai kata 'str' atau placeholder."
)

HINT_PRIORITY = ("add_new_stop", "improve_existing_stop", "increase_frequency")

AUTO_INSIGHT_PROMPT = (
    "Berikan analisis singkat dan tepat satu rekomendasi intervensi ASI untuk koridor ini "
    "berdasarkan konteks yang diberikan. Sebut nama subjek pada context.subject secara eksplisit. "
    "Halte pada context.bus_stops dihubungkan lewat kedekatan dalam radius buffer (bukan berarti berada "
    "tepat di koridor); sebut sebagai 'halte terdekat' beserta jarak distance_to_segment_m bila ada."
)

AUTO_INSIGHT_PROMPT_STOP = (
    "context.subject adalah halte. Analisis ini memakai segmen jalan TERDEKAT dari halte tersebut "
    "(dipetakan lewat jarak, bukan berarti halte berada di segmen itu). Katakan itu secara eksplisit, "
    "lalu sebut skor kualitas halte dari context.stop (skor_total, aksesibilitas, kondisi, lingkungan, "
    "jumlah_fasilitas, jumlah_kerusakan) sebelum memberi tepat satu rekomendasi intervensi ASI."
)

AUTO_INSIGHT_PROMPT_CORRIDOR = (
    "Berikan analisis singkat dan tepat satu rekomendasi intervensi ASI untuk sel grid pada "
    "context.subject. Sebutkan koridor yang MELINTASI sel itu (dari context.corridors) secara eksplisit; "
    "data koridor berasal dari perpotongan geometri dengan sel, bukan dari sel itu sendiri. "
    "Jika context.displayed_hour_label atau context.observed_hour ada, sebut analisis berlaku pada jam/tanggal itu "
    "dan pakai nilai hex_cell pada jam tersebut (data_status fallback = perkiraan, is_interpolated = hasil interpolasi). "
    "Gunakan HANYA angka dari context.hex_cell dan context.corridors; jangan memakai data sel grid lain."
)

AUTO_INSIGHT_PROMPT_HEX_ONLY = (
    "Tidak ada koridor yang terdeteksi melintasi sel grid pada context.subject. Katakan itu secara "
    "eksplisit, lalu berikan analisis berbasis context.hex_cell saja dan tepat satu rekomendasi ASI "
    "yang sesuai dengan klasifikasi_potensi pada hex_cell. "
    "Jika context.displayed_hour_label atau context.observed_hour ada, sebut analisis berlaku pada jam/tanggal itu. "
    "Gunakan HANYA angka dari context.hex_cell; jangan mengarang."
)

_RANKING_QUERY = re.compile(
    r"\b(tersibuk|tertinggi|terbesar|terbanyak|terburuk|terbaik|terjelek|terbersih|"
    r"paling\s+(sibuk|tinggi|besar|banyak|baik|buruk|jelek|bersih)|top|ranking|peringkat)\b",
    re.IGNORECASE,
)

# General/whole-dataset questions: plural or list phrasing, low/median superlatives.
_OVERVIEW_QUERY = re.compile(
    r"\b(koridor|jalan|segmen|segment)\s+(apa\s+saja|mana\s+saja|mana|semua|seluruh|daftar|list)\b"
    r"|\b(semua|seluruh|daftar|list)\s+(koridor|jalan|segmen|segment)\b"
    r"|\b(terendah|terkecil|tersedikit)\b"
    r"|\bpaling\s+(rendah|kecil|sedikit)\b"
    r"|\bnormal\b|\brata-rata\b",
    re.IGNORECASE,
)

# "koridor ini/itu/tersebut" points at the current map selection, not the whole
# dataset. "apa itu X" is a definition question, not a referential, so it is
# excluded here.
_REFERENTIAL = re.compile(r"(?<!\bapa\s)(?<!\bapakah\s)\b(ini|itu|tersebut)\b", re.IGNORECASE)

# Whole-grid activity-potential questions ("daerah dengan potensi aktivitas
# tertinggi"). Kept separate from corridor emission overview so the answer can
# rank hex cells, where the POI/population/volume AHP score actually lives.
_ACTIVITY_QUERY = re.compile(r"\b(potensi|aktivitas|activity)\b", re.IGNORECASE)
_SPATIAL_QUERY = re.compile(
    r"\b(daerah|wilayah|kawasan|zona|area|lokasi|sel|grid|hex)\b|\bdi\s+mana\b",
    re.IGNORECASE,
)

# A named/selected road wins over the whole-grid activity ranking.
_SEGMENT_NOUN = re.compile(r"\b(koridor|jalan|segmen|segment|ruas)\b", re.IGNORECASE)
_STOP_NOUN = re.compile(r"\b(halte|bus\s?stop|terminal|shelter|trayek|pemberhentian)\b", re.IGNORECASE)
_HEX_NOUN = re.compile(r"\b(grid|sel|hex|daerah|wilayah|kawasan|zona|area)\b", re.IGNORECASE)

# A referential ("ini/itu") must answer for the kind of object the user names;
# when that object is not selected, ask instead of narrating a different one.
_CLARIFY = {
    "segment": "Pilih dulu koridor/segmen jalan di peta, lalu tanyakan lagi tentang koridor itu.",
    "stop": "Pilih dulu halte di peta, lalu tanyakan lagi tentang halte itu.",
    "hex": "Pilih dulu sel grid di peta, lalu tanyakan lagi tentang sel itu.",
    None: "Pilih objek di peta (koridor, halte, atau sel grid) lalu tanyakan lagi.",
}


def _referential_target(message: str) -> str | None:
    text = message or ""
    if _STOP_NOUN.search(text):
        return "stop"
    if _SEGMENT_NOUN.search(text):
        return "segment"
    if _HEX_NOUN.search(text):
        return "hex"
    return None

# Requests that should get the structured ASI recommendation format.
_INTERVENTION_QUERY = re.compile(
    r"\b(intervensi|prioritas|asi|avoid|shift|improve|rekomendasi|saran|solusi|atasi|mengatasi|"
    r"perbaiki|perbaikan|cakupan|halte|armada|frekuensi|strategi|langkah)\b",
    re.IGNORECASE,
)

# Explanatory follow-ups ("kenapa ...", "kok ...") expect a conversational answer,
# not the structured report, even when they mention a topic noun like "halte".
_EXPLANATORY_QUERY = re.compile(r"^\s*(kenapa|mengapa|kok|gimana|bagaimana)\b", re.IGNORECASE)

# Explicit recommendation/analysis intent words (no bare topic nouns), used to keep
# a why-question in report style when it literally asks for a fix.
_EXPLICIT_RECOMMENDATION = re.compile(
    r"\b(intervensi|prioritas|rekomendasi|rekomendasikan|saran|sarankan|solusi|"
    r"strategi|langkah|atasi|mengatasi|perbaiki|perbaikan|asi|avoid|shift|improve)\b",
    re.IGNORECASE,
)

# Bus-stop questions that should retrieve the halte quality ranking, not corridor emissions.
_BUS_STOP_QUERY = re.compile(
    r"\b(halte|bus ?stop|terminal|shelter|trayek|pemberhentian)\b", re.IGNORECASE,
)
_BUS_STOP_RANKING = re.compile(
    r"\b(best|worst|terbaik|terburuk|terbagus|terjelek|paling\s+(baik|bagus|buruk|jelek)|"
    r"tertinggi|terendah|terbesar|terkecil|ranking|peringkat)\b",
    re.IGNORECASE,
)

# Colloquial corridor names -> canonical normalized name. Extend as needed.
_ALIAS_MAP = {
    "malioboro": "jalan malioboro",
    "jogja": "yogyakarta",
    "ugm": "universitas gadjah mada",
}


class HistoryTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    road_segment_id: str | None = None
    hex_id: int | None = None
    stop_id: str | None = None
    hour: str | None = None
    hour_label: str | None = None
    # "live" reads the newest observed fact per segment; anything else is the
    # static 24h profile addressed by ``hour``.
    time_mode: str | None = None
    history: list[HistoryTurn] = Field(default_factory=list)


def _normalize_name(name: str) -> str:
    text = (name or "").casefold()
    text = re.sub(r"\b(?:jl|jln)\.?\s+", "jalan ", text)
    text = re.sub(r"\bgg\.?\s+", "gang ", text)
    text = re.sub(r"\bkor\.?\s+", "koridor ", text)
    text = re.sub(r"[^\w\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _ALIAS_MAP.get(text, text)


def _is_ranking_query(message: str) -> bool:
    return bool(_RANKING_QUERY.search(message or ""))


def _is_overview_query(message: str) -> bool:
    """Whole-dataset question, not one about the selected/referred corridor."""
    text = message or ""
    if _REFERENTIAL.search(text):
        return False
    return bool(_OVERVIEW_QUERY.search(text) or _RANKING_QUERY.search(text))


def _is_activity_query(message: str) -> bool:
    """Whole-grid activity-potential question ("daerah dengan potensi aktivitas tertinggi").

    A road noun ("koridor", "jalan", ...) points at a corridor instead, and a
    referential ("ini/itu") must resolve to the active selection, so both are
    excluded here.
    """
    text = message or ""
    if _REFERENTIAL.search(text) or _SEGMENT_NOUN.search(text):
        return False
    if not _ACTIVITY_QUERY.search(text):
        return False
    return bool(_SPATIAL_QUERY.search(text) or _RANKING_QUERY.search(text) or "potensi" in text.casefold())


def _is_intervention_query(message: str) -> bool:
    return bool(_INTERVENTION_QUERY.search(message or ""))


def _is_bus_stop_query(message: str) -> bool:
    return bool(_BUS_STOP_QUERY.search(message or ""))


def _is_bus_stop_ranking(message: str) -> bool:
    """A halte quality/ranking question, as opposed to coverage or intervention."""
    return _is_bus_stop_query(message) and bool(_BUS_STOP_RANKING.search(message or ""))


def _classify_intent(message: str) -> str:
    """Response intent: ``analysis`` gets the structured ASI report; ``greeting``
    and ``general`` answer conversationally. Deterministic, no LLM call."""
    text = message or ""
    if _EXPLANATORY_QUERY.search(text) and not _EXPLICIT_RECOMMENDATION.search(text):
        return "general"
    if _is_intervention_query(text) and not _is_bus_stop_ranking(text):
        return "analysis"
    if _GREETING.search(text):
        return "greeting"
    return "general"


def _is_meta_query(message: str) -> bool:
    """Project-knowledge question, gated by the rollout kill-switch."""
    return bool(settings.BANGJO_META_SCOPE_ENABLED and is_meta_query(message or ""))


def _parse_hour(value: str | None) -> datetime | None:
    """Parse the client's active grid hour; unparseable input falls back to the anchor."""
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


async def _resolve_stop(db: AsyncSession, message: str) -> str | None:
    """Match a named halte by title or source_id (selection still wins for 'halte ini')."""
    rows = (await db.execute(select(SurveyStopObservation.source_id, SurveyStopObservation.title))).all()
    lower = _normalize_name(message)
    for source_id, title in rows:
        key = _normalize_name(title)
        if key and key in lower:
            return source_id
        stop_key = _normalize_name(source_id or "")
        if stop_key and stop_key in lower:
            return source_id
    return None


def _candidate_list(groups: list[list[dict]]) -> list[dict]:
    return [
        {"road_segment_id": members[0]["road_segment_id"], "name": members[0]["name"], "count": len(members)}
        for members in groups
    ]


async def _resolve_segment(
    db: AsyncSession, message: str, rows=None
) -> tuple[list[str] | None, list[dict]]:
    if rows is None:
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


async def _resolve_segment_cascade(
    db: AsyncSession, message: str
) -> tuple[list[str] | None, list[dict], str]:
    """Layer A (id/normalized name/alias) -> Layer B (embeddings) -> string fallback."""
    rows = (await db.execute(select(RoadSegment.road_segment_id, RoadSegment.name))).all()
    lower = _normalize_name(message)
    id_hits = [
        (rid, name)
        for rid, name in rows
        if _normalize_name(rid or "") and _normalize_name(rid) in lower
    ]
    if len(id_hits) == 1:
        return [id_hits[0][0]], [], "id"
    if len(id_hits) > 1:
        return None, [
            {"road_segment_id": rid, "name": name, "count": 1} for rid, name in id_hits
        ], "ambiguous"
    groups: dict[str, list[dict]] = {}
    for rid, name in rows:
        key = _normalize_name(name)
        if key:
            groups.setdefault(key, []).append({"road_segment_id": rid, "name": name})
    named = [members for key, members in groups.items() if key in lower or (lower and lower in key)]
    if len(named) == 1:
        return [member["road_segment_id"] for member in named[0]], [], "alias"
    if len(named) > 1:
        return None, _candidate_list(named), "ambiguous"
    embedded = await resolve_by_embedding(db, message)
    if embedded:
        return embedded, [], "embedding"
    ids, candidates = await _resolve_segment(db, message, rows)
    return ids, candidates, "string"


async def _dispatch_referential(db: AsyncSession, payload: "ChatRequest") -> dict:
    """Resolve a referential ("ini/itu/tersebut") to the selection matching its subject.

    "koridor ini" must answer for a corridor, "halte ini" for a halte, and
    "sel/grid ini" for a hex cell. When the matching object is not selected the
    route asks the user to pick one, instead of silently narrating whichever
    selection happens to be active.
    """
    target = _referential_target(payload.message)
    if target == "stop":
        if payload.stop_id:
            return {"kind": "stop", "stop_id": payload.stop_id}
        return {"kind": "clarify", "detail": _CLARIFY["stop"]}
    if target == "hex":
        if payload.hex_id is not None:
            return {"kind": "hex", "hex_id": payload.hex_id}
        return {"kind": "clarify", "detail": _CLARIFY["hex"]}
    if target == "segment":
        if payload.road_segment_id:
            return {"kind": "segment", "segment_ids": [payload.road_segment_id]}
        # A selected hex still answers "koridor ini" via the corridors crossing it.
        if payload.hex_id is not None and db is not None:
            crossing = await segments_for_hex(db, payload.hex_id)
            if crossing:
                return {"kind": "segment", "segment_ids": list(crossing)}
        return {"kind": "clarify", "detail": _CLARIFY["segment"]}
    if payload.hex_id is not None:
        return {"kind": "hex", "hex_id": payload.hex_id}
    if payload.stop_id:
        return {"kind": "stop", "stop_id": payload.stop_id}
    if payload.road_segment_id:
        return {"kind": "segment", "segment_ids": [payload.road_segment_id]}
    return {"kind": "clarify", "detail": _CLARIFY[None]}


async def _dispatch_scope_ex(db: AsyncSession, payload: "ChatRequest") -> tuple[dict, bool]:
    """Decide which context to retrieve for a chat turn.

    Precedence: halte quality ranking -> selected/named halte -> whole-grid
    activity potential -> whole-dataset corridor overview -> named corridor ->
    active map selection -> overview. Referential wording ("ini", "itu",
    "tersebut") resolves to the active selection instead of name matching, since
    the user is pointing at the visualization.

    The second value is ``True`` when the current message itself resolved the
    scope. It is ``False`` for the silent fallbacks to the active selection or a
    bare overview, which is the signal that question-driven retrieval (the LLM
    planner) should run instead.
    """
    message = payload.message
    referential = bool(_REFERENTIAL.search(message))

    if _is_bus_stop_ranking(message):
        return {"kind": "bus_stops"}, True
    if _is_bus_stop_query(message) and payload.stop_id and (referential or not _is_ranking_query(message)):
        return {"kind": "stop", "stop_id": payload.stop_id}, True
    if _is_bus_stop_query(message):
        named_stop = await _resolve_stop(db, message)
        if named_stop:
            return {"kind": "stop", "stop_id": named_stop}, True
    if _is_activity_query(message):
        return {"kind": "hex_activity"}, True
    if _is_overview_query(message):
        return {"kind": "overview"}, True
    if _is_meta_query(message):
        return {"kind": "meta"}, True

    if referential:
        return await _dispatch_referential(db, payload), True

    ids, candidates, method = await _resolve_segment_cascade(db, message)
    if ids:
        return {"kind": "segment", "segment_ids": ids}, True
    if method == "ambiguous" and candidates:
        return {"kind": "ambiguous", "candidates": candidates}, True

    if payload.hex_id is not None:
        return {"kind": "hex", "hex_id": payload.hex_id}, False
    if payload.stop_id:
        return {"kind": "stop", "stop_id": payload.stop_id}, False
    if payload.road_segment_id:
        return {"kind": "segment", "segment_ids": [payload.road_segment_id]}, False
    return {"kind": "overview"}, False


async def _dispatch_scope(db: AsyncSession, payload: "ChatRequest") -> dict:
    scope, _ = await _dispatch_scope_ex(db, payload)
    return scope


async def _build_scope_context(
    db: AsyncSession, scope: dict, payload: "ChatRequest"
) -> tuple[dict | None, str | None, dict | None]:
    """Build the prompt context + label for a resolved scope.

    Returns ``(context, label, None)`` on success, or ``(None, None, response)``
    when the requested object does not exist (caller returns ``response`` as-is).
    Shared by the deterministic router and the LLM planner so both paths narrate
    the exact same evidence.
    """
    hour = _parse_hour(payload.hour)
    live = payload.time_mode == "live"
    kind = scope["kind"]
    if kind == "overview":
        context = overview_payload(await build_overview_context(db))
        label = f"Ringkasan {context.get('jumlah_koridor')} koridor"
    elif kind == "meta":
        context = build_meta_context(payload.message)
        label = "Pengetahuan proyek"
    elif kind == "bus_stops":
        context = bus_stop_payload(await build_bus_stop_overview_context(db))
        label = f"Ringkasan {context.get('jumlah_dinilai')} halte dinilai"
    elif kind == "hex_activity":
        context = activity_overview_payload(await build_activity_overview_context(db, None if live else hour, live))
        label = f"Ringkasan potensi aktivitas {context.get('jumlah_sel_dinilai')} sel"
    elif kind == "hex":
        built = await build_hex_context(db, scope["hex_id"], None if live else hour, live=live)
        if built is None:
            return None, None, {"needs_selection": True, "candidates": [], "answer": None, "context_label": None,
                                "detail": f"Hex {scope['hex_id']} tidak ditemukan pada grid aktivitas.",
                                "blocked": False, "message": None}
        corridors = _merge_contexts(built["corridor_contexts"]) if built["corridor_contexts"] else None
        context = {
            "subject": {"type": "hex", "id": scope["hex_id"]},
            "data_mode": "live" if live else None,
            "displayed_hour_label": None if live else payload.hour_label,
            "observed_hour": built.get("observed_hour"),
            "hex_cell": built["hex_cell"],
            "corridors": corridors,
        }
        label = f"grid Hex {scope['hex_id']}"
        if payload.hour_label and not live:
            label += f" · {payload.hour_label}"
        if corridors:
            label += f" · {corridors['segment']['name']}"
    elif kind == "stop":
        context = await build_stop_context(db, scope["stop_id"])
        if context is None:
            return None, None, {"needs_selection": True, "candidates": [], "answer": None, "context_label": None,
                                "detail": f"Halte '{scope['stop_id']}' tidak ditemukan.",
                                "blocked": False, "message": None}
        label = f"{context['stop']['title']} ({scope['stop_id']})"
    else:
        segment_ids = scope["segment_ids"]
        contexts = [context for context in [await build_context(db, sid) for sid in segment_ids] if context]
        if not contexts:
            return None, None, {"needs_selection": True, "candidates": [], "answer": None, "context_label": None,
                                "detail": f"Segmen '{segment_ids[0]}' tidak ditemukan.",
                                "blocked": False, "message": None}
        context = _merge_contexts(contexts)
        chunk_count = context["segment"]["chunk_count"]
        label = (f"{context['segment']['name']} ({chunk_count} segmen)" if chunk_count > 1
                 else f"{context['segment']['name']} ({segment_ids[0]})")
    return context, label, None


async def _cache_get(key: str) -> str | None:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        try:
            value = await client.get(key)
        finally:
            await client.aclose()
        return value.decode() if isinstance(value, bytes) else value
    except Exception:
        logger.warning("bangjo_cache_get_failed", exc_info=True)
        return None


async def _cache_set(key: str, value: str, ttl_seconds: int) -> None:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        try:
            await client.setex(key, ttl_seconds, value)
        finally:
            await client.aclose()
    except Exception:
        logger.warning("bangjo_cache_set_failed", exc_info=True)


def _chat_cache_key(message: str, scope: dict, history: list[dict]) -> str:
    """Cache identity includes the resolved scope and active filters (hour), so a
    cached answer can never describe a different selection than the one on screen."""
    digest = hashlib.sha256()
    digest.update(_normalize_name(message).encode("utf-8"))
    digest.update(json.dumps(scope, sort_keys=True, default=str).encode("utf-8"))
    for turn in history[-4:]:
        digest.update(f"{turn['role']}:{turn['content']}".encode("utf-8"))
    return f"bangjo:chat:{digest.hexdigest()}"


class BangJoLLMError(RuntimeError):
    """Raised when the LLM cannot produce a usable answer (no fallback)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


_THINK_RE = re.compile(r"<think(?:ing)?>.*?(?:</think(?:ing)?>|$)", re.IGNORECASE | re.DOTALL)


def _strip_reasoning(text: str) -> str:
    """Drop literal <think>...</think> blocks a raw reasoning format leaks into content."""
    return _THINK_RE.sub("", text or "").strip()


def _validate_markdown(raw: str) -> str:
    """Accept only non-empty, non-placeholder prose; anything else retries."""
    text = raw.strip()
    for fence in ("```markdown", "```md", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
            break
    text = text.strip().removesuffix("```").strip()
    collapsed = text.casefold()
    if len(text) < 20:
        raise ValueError("LLM answer too short")
    if collapsed in {"str", "[str]", "...", "str.", "tidak tersedia"}:
        raise ValueError("LLM answer is a placeholder")
    if text.startswith("{"):
        raise ValueError("LLM answer is JSON, not markdown")
    return text


def _history_turns(history) -> list[dict]:
    turns = []
    for turn in history or []:
        role = turn.get("role") if isinstance(turn, dict) else getattr(turn, "role", None)
        content = turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", None)
        if role in ("user", "assistant"):
            turns.append({"role": role, "content": content})
    return turns


_RETRYABLE_LLM_STATUS = (429, 500, 502, 503, 504)


def _llm_attempts() -> list[dict]:
    """Primary attempt, plus an optional fallback model/provider."""
    attempts = [{
        "model": settings.BANGJO_MODEL,
        "base_url": settings.BANGJO_BASE_URL,
        "api_key": settings.GROQ_API_KEY,
    }]
    if settings.BANGJO_FALLBACK_MODEL and settings.BANGJO_FALLBACK_MODEL != settings.BANGJO_MODEL:
        attempts.append({
            "model": settings.BANGJO_FALLBACK_MODEL,
            "base_url": settings.BANGJO_FALLBACK_BASE_URL or settings.BANGJO_BASE_URL,
            "api_key": settings.BANGJO_FALLBACK_API_KEY or settings.GROQ_API_KEY,
        })
    return attempts


def _estimate_tokens(text: str) -> int:
    """Deliberately conservative char estimate (chars/2).

    JSON, numbers, and Indonesian tokenize far denser than the old chars/4 guess;
    over-estimating only trims a little sooner, while under-estimating is what let
    ``prompt + max_tokens`` cross Groq's free-tier ceiling and return 413.
    """
    return max(1, len(text or "") // 2)


# Prompt headroom kept free beyond the output reservation, for provider-side drift.
BANGJO_SAFETY_TOKENS = 200
_TREND_QUERY = re.compile(
    r"\b(tren|trend|per jam|tiap jam|sepanjang hari|naik|turun|puncak|jam sibuk|pola)\b",
    re.IGNORECASE,
)


def _input_budget() -> int:
    """Prompt allowance once the full (untrimmed) output reservation is set aside."""
    return max(
        0,
        settings.BANGJO_REQUEST_TOKEN_LIMIT - settings.BANGJO_MAX_TOKENS - BANGJO_SAFETY_TOKENS,
    )


def _series_summary(series: list[dict] | None) -> dict | None:
    """One-line summary of a 24h series so it doesn't dominate every prompt."""
    points = series or []
    if not points:
        return None
    present = []
    for point in points:
        values = [value for value in (point.get("emissions_kg_h") or {}).values() if value is not None]
        if values:
            present.append((point.get("hour"), sum(values)))
    summary = {
        "jumlah_jam": len(points),
        "jumlah_jam_interpolasi": sum(1 for point in points if point.get("is_interpolated")),
        "catatan": "ringkasan jam; minta 'tren per jam' bila perlu rincian tiap jam",
    }
    if present:
        peak_hour, peak_total = max(present, key=lambda item: item[1])
        low_hour, low_total = min(present, key=lambda item: item[1])
        summary.update({
            "jam_puncak": peak_hour,
            "total_tertinggi_kg_h": round(peak_total, 3),
            "jam_terendah": low_hour,
            "total_terendah_kg_h": round(low_total, 3),
        })
    return summary


def _compact_context(context: dict, message: str, minimal: bool = False) -> dict:
    """Shrink the context for the prompt only; the full context is still built.

    ``minimal`` drops the series and stop list entirely (last-resort fit). Full
    hourly series is kept only when the question is time/trend-shaped.
    """
    compact = dict(context)
    compact.pop("generated_at", None)

    def shrink(inner: dict) -> dict:
        out = dict(inner)
        series = out.pop("hourly_series", None)
        if series and _TREND_QUERY.search(message or ""):
            out["hourly_series"] = series
        else:
            summary = _series_summary(series)
            if summary:
                out["hourly_series_ringkasan"] = summary
        stops = out.get("bus_stops")
        if stops:
            ordered = sorted(stops, key=lambda stop: stop.get("distance_to_segment_m") or 1e9)
            out["bus_stops"] = [] if minimal else ordered[:5]
        potential = out.get("activity_potential")
        if isinstance(potential, dict):
            potential = dict(potential)
            potential.pop("hex_ids", None)
            out["activity_potential"] = potential
        return out

    if any(key in compact for key in ("segment", "bus_stops", "hourly_series")):
        compact = shrink(compact)
    hex_cell = compact.get("hex_cell")
    if isinstance(hex_cell, dict):
        hex_cell = dict(hex_cell)
        breakdown = hex_cell.get("poi_breakdown")
        if isinstance(breakdown, dict):
            top = sorted(breakdown.items(), key=lambda item: item[1] or 0, reverse=True)[:8]
            hex_cell["poi_breakdown"] = dict(top)
        compact["hex_cell"] = hex_cell
    corridors = compact.get("corridors")
    if isinstance(corridors, dict):
        compact["corridors"] = shrink(corridors)
    return compact


def _user_turn(message: str, context: dict) -> str:
    return f"Konteks:\n{json.dumps(context, ensure_ascii=False)}\n\nPertanyaan: {message}"


def _fit_messages(
    system: str, user_content: str, history: list[dict], tail: list[dict] | None = None
) -> list[dict] | None:
    """System + as much recent history as fits the prompt budget (newest kept).

    Returns ``None`` when even the current user turn does not fit, so the caller
    compacts the context. Output tokens are never reduced; input is trimmed.
    """
    budget = _input_budget()
    tail = tail or []
    used = (
        _estimate_tokens(system)
        + _estimate_tokens(user_content)
        + sum(_estimate_tokens(turn.get("content") or "") for turn in tail)
    )
    if used > budget:
        return None
    kept: list[dict] = []
    for turn in reversed(history):
        cost = _estimate_tokens(turn.get("content") or "")
        if used + cost > budget:
            break
        kept.append(turn)
        used += cost
    kept.reverse()
    return [{"role": "system", "content": system}, *kept, {"role": "user", "content": user_content}, *tail]


def _fit_context_conversation(
    message: str, context: dict, history: list[dict], style: str
) -> tuple[list[dict], dict]:
    """Pick the smallest context that fits, then fit history around it."""
    system = _system_prompt(style)
    minimal = _compact_context(context, message, minimal=True)
    for candidate in (context, _compact_context(context, message), minimal):
        conversation = _fit_messages(system, _user_turn(message, candidate), history)
        if conversation is not None:
            return conversation, candidate
    # Extremely large context: send the minimal form without history, never 413.
    return [{"role": "system", "content": system}, {"role": "user", "content": _user_turn(message, minimal)}], minimal


async def _ask_llm(
    message: str, context: dict, history, timings: dict | None = None, style: str = "general"
) -> dict:
    if not settings.GROQ_API_KEY:
        raise BangJoLLMError("no_api_key")
    turns = _history_turns(history)
    system = _system_prompt(style)
    conversation, used_context = _fit_context_conversation(message, context, turns, style)
    # Output allowance stays at the configured maximum; input is what shrinks.
    max_tokens = settings.BANGJO_MAX_TOKENS
    estimated_input = sum(_estimate_tokens(turn.get("content") or "") for turn in conversation)
    started = time.monotonic()
    reason = "llm_error"

    for attempt in _llm_attempts():
        base = {"model": attempt["model"], "max_tokens": max_tokens}
        url = attempt["base_url"]
        headers = {"Authorization": f"Bearer {attempt['api_key']}", "Content-Type": "application/json"}
        result: dict | None = None
        llm_ms: float | None = None
        parse_ms: float | None = None

        async def call(client: httpx.AsyncClient, messages: list[dict]) -> dict:
            body = {
                **base,
                "messages": messages,
                **({"reasoning_format": settings.BANGJO_REASONING_FORMAT}
                   if settings.BANGJO_REASONING_FORMAT else {}),
                **({"reasoning_effort": settings.BANGJO_REASONING_EFFORT}
                   if settings.BANGJO_REASONING_EFFORT else {}),
            }
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            choice = (data.get("choices") or [{}])[0]
            return {
                "raw": _strip_reasoning(choice.get("message", {}).get("content") or ""),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage") or {},
            }

        def diagnostics(reason: str | None = None) -> dict:
            extra = {
                "model": attempt["model"],
                "finish_reason": result.get("finish_reason") if result else None,
                "usage": result.get("usage") if result else None,
                "raw_length": len(result["raw"]) if result else 0,
                "raw_preview": result["raw"][:500] if result else "",
                "estimated_input_tokens": estimated_input,
                "max_tokens": max_tokens,
            }
            if reason:
                extra["reason"] = reason
            if settings.BANGJO_DEBUG_RAW and result:
                extra["raw_text"] = result["raw"]
            return extra

        try:
            async with httpx.AsyncClient(timeout=settings.BANGJO_TIMEOUT_SECONDS) as client:
                result = await call(client, conversation)
                if result["finish_reason"] == "length":
                    reason = "length"
                    logger.warning("bangjo_llm_attempt_failed", extra=diagnostics(reason))
                    continue
                llm_ms = round((time.monotonic() - started) * 1000, 2)
                parse_started = time.monotonic()
                try:
                    content = _validate_markdown(result["raw"])
                except ValueError:
                    logger.warning("bangjo_llm_parse_failed", extra=diagnostics())
                    tail = [{"role": "assistant", "content": result["raw"]},
                            {"role": "user", "content": CORRECTIVE_PROMPT}]
                    retry = _fit_messages(system, _user_turn(message, used_context), turns, tail)
                    if retry is None:
                        retry = [{"role": "system", "content": system},
                                 {"role": "user", "content": _user_turn(message, used_context)}, *tail]
                    result = await call(client, retry)
                    if result["finish_reason"] == "length":
                        reason = "length"
                        logger.warning("bangjo_llm_attempt_failed", extra=diagnostics(reason))
                        continue
                    content = _validate_markdown(result["raw"])
                parse_ms = round((time.monotonic() - parse_started) * 1000, 2)
            logger.info("bangjo_llm_call", extra={
                "source": "llm",
                "latency_s": round(time.monotonic() - started, 3),
                "input_tokens": result["usage"].get("prompt_tokens"),
                "output_tokens": result["usage"].get("completion_tokens"),
                "finish_reason": result["finish_reason"],
                "model": attempt["model"],
                "llm_ms": llm_ms,
                "parse_ms": parse_ms,
                "estimated_input_tokens": estimated_input,
                "max_tokens": max_tokens,
                **(timings or {}),
            })
            return {"content": content, "source": "llm"}
        except httpx.TimeoutException:
            reason = "timeout"
            logger.exception("bangjo_llm_attempt_failed", extra=diagnostics(reason))
            continue
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            reason = "payload_too_large" if status == 413 else "http_error"
            logger.exception("bangjo_llm_attempt_failed", extra={**diagnostics(reason), "status": status})
            if status == 413:
                # Defense in depth: the budget should prevent this, but if the
                # provider still rejects it, retry once with no history and the
                # most compact context instead of failing the user.
                minimal = _compact_context(context, message, minimal=True)
                reduced = _fit_messages(system, _user_turn(message, minimal), [])
                if reduced is not None:
                    try:
                        async with httpx.AsyncClient(timeout=settings.BANGJO_TIMEOUT_SECONDS) as client:
                            result = await call(client, reduced)
                        content = _validate_markdown(result["raw"])
                        logger.info("bangjo_llm_call", extra={
                            "source": "llm_reduced", "model": attempt["model"], **(timings or {}),
                        })
                        return {"content": content, "source": "llm"}
                    except Exception:
                        logger.warning("bangjo_llm_reduced_failed", exc_info=True)
                raise BangJoLLMError(reason)
            if status not in _RETRYABLE_LLM_STATUS:
                raise BangJoLLMError(reason)
            continue
        except ValueError:
            logger.warning("bangjo_llm_attempt_failed", extra=diagnostics("parse_error"))
            raise BangJoLLMError("parse_error")
        except BangJoLLMError:
            raise
        except Exception:
            logger.exception("bangjo_llm_attempt_failed", extra=diagnostics("llm_error"))
            raise BangJoLLMError("llm_error")

    logger.warning("bangjo_llm_failed", extra={"reason": reason, **(timings or {})})
    raise BangJoLLMError(reason)


# --- question-driven retrieval (tool-calling planner) -----------------------
# When the deterministic router falls through to the active map selection (a
# stale object from the previous turn), the model picks what to fetch based on
# the latest question. It only selects a retrieval target; the existing context
# builders still produce every number, so numeric grounding is unchanged.

_PLANNER_SYSTEM = (
    "Anda adalah router pengambilan data untuk Bang Jo (WebGIS EcoTraffic Yogyakarta). "
    "Panggil TEPAT SATU fungsi yang mengambil data untuk menjawab PERTANYAAN TERBARU pengguna. "
    "Fokus HANYA pada pertanyaan terbaru: bila pengguna menyebut koridor/jalan/halte/sel yang baru, "
    "abaikan topik sebelumnya. Gunakan riwayat hanya untuk memahami rujukan seperti 'itu', 'yang tadi', atau 'lainnya'. "
    "get_segment dipakai untuk nama jalan ('Jalan Malioboro') maupun ID segmen ('SEG-0022'). "
    "get_bus_stop dipakai untuk nama atau ID halte. list_corridors untuk peringkat seluruh koridor. "
    "rank_bus_stops untuk peringkat kualitas seluruh halte. rank_activity_cells untuk peringkat potensi "
    "seluruh sel grid. get_activity_cell untuk satu sel grid. "
    "get_project_info untuk pertanyaan tentang proyek/dashboard itu sendiri (apa itu EcoTraffic, cara "
    "kerja skor aktivitas atau emisi, sumber data, beda live vs replay, kemampuan Bang Jo). "
    "Jangan mengarang angka dan jangan menjawab pertanyaan; hanya panggil fungsi."
)

_PLANNER_TOOLS = [
    {"type": "function", "function": {
        "name": "get_segment",
        "description": "Ambil data satu koridor/segmen jalan dari nama atau ID (contoh: 'Jalan Malioboro', 'SEG-0022').",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Nama jalan atau ID segmen yang ditanyakan"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "list_corridors",
        "description": "Ambil ringkasan peringkat seluruh koridor (emisi, kebutuhan intervensi).",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "rank_bus_stops",
        "description": "Ambil peringkat kualitas seluruh halte.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_bus_stop",
        "description": "Ambil data kualitas satu halte dari nama atau ID.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Nama atau ID halte"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "rank_activity_cells",
        "description": "Ambil peringkat potensi aktivitas seluruh sel grid.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_activity_cell",
        "description": "Ambil data satu sel grid aktivitas dari ID sel.",
        "parameters": {"type": "object", "properties": {
            "hex_id": {"type": "integer", "description": "ID sel grid"}}, "required": ["hex_id"]}}},
    {"type": "function", "function": {
        "name": "get_project_info",
        "description": "Ambil penjelasan tentang proyek EcoTraffic-GIS: apa itu, cara kerja skor aktivitas/emisi, sumber data, mode live vs replay, dan kemampuan Bang Jo.",
        "parameters": {"type": "object", "properties": {}}}},
]


def _parse_tool_calls(message: dict) -> list[dict]:
    calls: list[dict] = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        name = function.get("name")
        if not name:
            continue
        raw = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (TypeError, ValueError):
            arguments = {}
        calls.append({"name": name, "arguments": arguments})
    return calls


async def _plan_retrieval(message: str, history) -> list[dict] | None:
    """Ask the model which single dataset to fetch; ``None`` on any failure."""
    return await _planner_call(message, history, _PLANNER_SYSTEM)


async def _plan_repair(
    message: str, history, failure_reason: str, candidates: list[str] | None
) -> list[dict] | None:
    """The single bounded re-pick: tell the planner what failed and why.

    Kept separate from :func:`_plan_retrieval` so the normal path stays a plain
    two-argument call and test doubles keep working.
    """
    hint = f"Percobaan sebelumnya gagal ({failure_reason}). "
    if candidates:
        hint += f"Kandidat yang mungkin: {', '.join(candidates)}. "
    hint += (
        "Pilih ulang fungsi yang paling tepat, atau get_project_info bila pertanyaannya "
        "tentang proyek/dashboard."
    )
    return await _planner_call(message, history, f"{_PLANNER_SYSTEM}\n{hint}")


async def _planner_call(message: str, history, system: str) -> list[dict] | None:
    if not settings.BANGJO_TOOL_ROUTING_ENABLED or not settings.GROQ_API_KEY:
        return None
    planner_turns = [
        {"role": "system", "content": system},
        *_history_turns(history),
        {"role": "user", "content": message},
    ]
    for attempt in _llm_attempts():
        headers = {"Authorization": f"Bearer {attempt['api_key']}", "Content-Type": "application/json"}
        body = {
            "model": attempt["model"],
            "max_tokens": settings.BANGJO_PLANNER_MAX_TOKENS,
            "messages": planner_turns,
            "tools": _PLANNER_TOOLS,
            "tool_choice": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.BANGJO_TIMEOUT_SECONDS) as client:
                response = await client.post(attempt["base_url"], headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
            choice = (data.get("choices") or [{}])[0]
            calls = _parse_tool_calls(choice.get("message") or {})
            if calls:
                return calls
            return None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in _RETRYABLE_LLM_STATUS:
                continue
            logger.warning("bangjo_planner_failed", extra={"status": status})
            return None
        except Exception:
            logger.warning("bangjo_planner_failed", exc_info=True)
            return None
    return None


async def _tool_calls_to_scope(db: AsyncSession, calls: list[dict], payload: "ChatRequest") -> dict | None:
    """Resolve the planner's single tool call into a retrieval scope.

    One subject per turn keeps the existing single-context prompt contract; the
    planner prompt is explicit about calling exactly one function.
    """
    call = calls[0]
    name = call["name"]
    args = call["arguments"] or {}
    if name in ("get_segment", "get_bus_stop"):
        query = str(args.get("query") or "").strip()
        if not query:
            return None
        if name == "get_bus_stop":
            stop_id = await _resolve_stop(db, query)
            return {"kind": "stop", "stop_id": stop_id} if stop_id else None
        ids, candidates, method = await _resolve_segment_cascade(db, query)
        if ids:
            return {"kind": "segment", "segment_ids": ids}
        if method == "ambiguous" and candidates:
            return {"kind": "ambiguous", "candidates": candidates}
        return None
    if name == "list_corridors":
        return {"kind": "overview"}
    if name == "rank_bus_stops":
        return {"kind": "bus_stops"}
    if name == "rank_activity_cells":
        return {"kind": "hex_activity"}
    if name == "get_activity_cell":
        try:
            return {"kind": "hex", "hex_id": int(args.get("hex_id"))}
        except (TypeError, ValueError):
            return None
    if name == "get_project_info":
        return {"kind": "meta"}
    return None


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
            "data_status": primary.get("data_status"),
            "is_estimated": any(segment.get("is_estimated") for segment in segments),
            "borrowed_from": primary.get("borrowed_from"),
            "is_static": any(segment.get("is_static") for segment in segments),
            "is_interpolated": any(segment.get("is_interpolated") for segment in segments),
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


def _repair_candidates(context: dict) -> list[str]:
    """Short, context-derived name list for the one bounded repair re-pick."""
    names: list[str] = []
    for key in ("emisi_tertinggi", "emisi_terendah", "halte_terbaik", "halte_terburuk"):
        for row in context.get(key) or []:
            name = row.get("nama")
            if name and name not in names:
                names.append(name)
    return names[:5]


def _deterministic_repair(scope: dict, verdict: str) -> dict | None:
    """Free fallback scope for an empty result, tried before any repair LLM call.

    Only a whole-dataset overview can rescue an empty ranked scope; a degenerate
    per-entity result is left to the bounded LLM repair, since guessing another
    entity would silently answer a different question.
    """
    if verdict != "empty":
        return None
    if scope.get("kind") in ("hex_activity", "bus_stops", "hex"):
        return {"kind": "overview"}
    return None


@router.post("/bangjo")
async def bangjo_chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    started = time.monotonic()
    timings: dict = {"cache_hit": False, "blocked": False}
    try:
        gate = screen_query(payload.message)
    except Exception:
        logger.warning("bangjo_guardrail_error", exc_info=True)
        gate = {"blocked": False, "reason": None, "message": None}
    timings["guardrail_ms"] = round((time.monotonic() - started) * 1000, 2)
    if gate["blocked"]:
        timings["blocked"] = True
        logger.info("bangjo_llm_call", extra={**timings, "source": "blocked"})
        return {"needs_selection": False, "answer": None, "context_label": None,
                "blocked": True, "message": gate["message"]}

    history = sanitize_history(payload.history)
    style = "intervention" if _classify_intent(payload.message) == "analysis" else "general"
    scope, confident = await _dispatch_scope_ex(db, payload)
    if scope["kind"] == "ambiguous":
        # Several corridors match by name; only a real ambiguity asks the user.
        timings["retrieval_ms"] = round((time.monotonic() - started) * 1000, 2)
        return {"needs_selection": True, "candidates": scope["candidates"], "answer": None,
                "context_label": None, "blocked": False, "message": None}
    if scope["kind"] == "clarify":
        # A referential pointed at an object the user has not selected.
        timings["retrieval_ms"] = round((time.monotonic() - started) * 1000, 2)
        return {"needs_selection": True, "candidates": [], "answer": None, "context_label": None,
                "detail": scope["detail"], "blocked": False, "message": None}
    timings["resolve_ms"] = round((time.monotonic() - started) * 1000, 2)

    cache_scope = {**scope, "hour": payload.hour, "hour_label": payload.hour_label, "time_mode": payload.time_mode}
    cache_key = _chat_cache_key(payload.message, cache_scope, history)
    cached = await _cache_get(cache_key)
    if cached:
        try:
            response = json.loads(cached)
            response["blocked"] = False
            response["message"] = None
            timings["cache_hit"] = True
            logger.info("bangjo_llm_call", extra={**timings, "source": "cache"})
            return response
        except ValueError:
            pass

    context_started = time.monotonic()
    planner_used = False
    # Retrieval-side LLM calls (initial plan + one repair) are capped at two per
    # question; answer generation is separate and unchanged.
    planner_calls = 0
    if not confident and _classify_intent(payload.message) != "greeting":
        # Deterministic routing only reached the active map selection, which may
        # be the previous turn's object. Let the model choose the dataset the
        # latest question actually asks about before narrating.
        calls = await _plan_retrieval(payload.message, history)
        planner_calls += 1
        planned_scope = await _tool_calls_to_scope(db, calls, payload) if calls else None
        if planned_scope and planned_scope["kind"] == "ambiguous":
            timings["retrieval_ms"] = round((time.monotonic() - started) * 1000, 2)
            return {"needs_selection": True, "candidates": planned_scope["candidates"], "answer": None,
                    "context_label": None, "blocked": False, "message": None}
        if planned_scope:
            scope = planned_scope
            planner_used = True
    if not confident and not planner_used and gate.get("reason") == NO_SCOPE_MATCH:
        # On-topic but neither the data scopes nor the planner found anything:
        # decline as a last resort instead of narrating an unrelated fallback.
        timings["retrieval_ms"] = round((time.monotonic() - started) * 1000, 2)
        logger.info("bangjo_llm_call", extra={**timings, "source": "declined"})
        return {"needs_selection": False, "answer": None, "context_label": None,
                "blocked": True, "message": DECLINE_MESSAGE}
    timings["planner_used"] = planner_used
    context, label, error = await _build_scope_context(db, scope, payload)
    if error is not None:
        timings["retrieval_ms"] = round((time.monotonic() - started) * 1000, 2)
        return error
    verdict = verify_context_result(context, scope)
    timings["verify"] = verdict
    if verdict != "ok":
        # Deterministic repair first (free): a whole-dataset overview can rescue
        # an empty ranked scope without another LLM call.
        fallback = _deterministic_repair(scope, verdict)
        if fallback and fallback != scope:
            fallback_context, fallback_label, fallback_error = await _build_scope_context(db, fallback, payload)
            if fallback_error is None:
                context, label, scope, planner_used = fallback_context, fallback_label, fallback, True
                verdict = verify_context_result(context, scope)
    if verdict != "ok" and planner_calls < 2:
        # One bounded repair: re-pick a scope once, then stop. Never loops.
        calls = await _plan_repair(
            payload.message, history, failure_reason=verdict, candidates=_repair_candidates(context)
        )
        planner_calls += 1
        repaired = await _tool_calls_to_scope(db, calls, payload) if calls else None
        if repaired and repaired.get("kind") != "ambiguous" and repaired != scope:
            repaired_context, repaired_label, repaired_error = await _build_scope_context(db, repaired, payload)
            if repaired_error is None:
                context, label, scope, planner_used = repaired_context, repaired_label, repaired, True
    timings["planner_calls"] = planner_calls
    timings["context_ms"] = round((time.monotonic() - context_started) * 1000, 2)
    try:
        answer = await _ask_llm(payload.message, context, history, timings, style=style)
    except BangJoLLMError as exc:
        logger.warning("bangjo_llm_unavailable", extra={**timings, "reason": exc.reason})
        raise HTTPException(status_code=502, detail=f"Maaf, Bang Jo tidak dapat dihubungi ({exc.reason}). Coba lagi.")
    response = {"needs_selection": False, "answer": answer, "context_label": label,
                "blocked": False, "message": None}
    await _cache_set(cache_key, json.dumps(response), settings.BANGJO_CACHE_TTL_SECONDS)
    return response


class AutoInsightRequest(BaseModel):
    road_segment_id: str | None = None
    hex_id: int | None = None
    stop_id: str | None = None
    hour: str | None = None
    hour_label: str | None = None
    time_mode: str | None = None


async def _entity_segment_ids(db: AsyncSession, payload: AutoInsightRequest) -> tuple[list[str], dict | None]:
    if payload.road_segment_id:
        return [payload.road_segment_id], {"type": "segment", "id": payload.road_segment_id}
    if payload.hex_id is not None:
        return list(await segments_for_hex(db, payload.hex_id)), {"type": "hex", "id": payload.hex_id}
    if payload.stop_id:
        segment_id = await segment_for_stop(db, payload.stop_id)
        return ([segment_id] if segment_id else []), {"type": "stop", "id": payload.stop_id}
    return [], None


@router.post("/bangjo/auto-insight")
async def bangjo_auto_insight(payload: AutoInsightRequest, db: AsyncSession = Depends(get_db)):
    if payload.road_segment_id:
        entity = {"type": "segment", "id": payload.road_segment_id}
    elif payload.hex_id is not None:
        entity = {"type": "hex", "id": payload.hex_id}
    elif payload.stop_id:
        entity = {"type": "stop", "id": payload.stop_id}
    else:
        return {"needs_selection": True, "answer": None, "context_label": None, "entity": None,
                "cached": False, "detail": "Pilih segmen, sel grid, atau halte terlebih dahulu."}

    hour = _parse_hour(payload.hour)
    live = payload.time_mode == "live"
    cache_key = f"bangjo:autoinsight:{entity['type']}:{entity['id']}:{payload.hour or ''}:{payload.time_mode or ''}"
    cached = await _cache_get(cache_key)
    if cached:
        try:
            response = json.loads(cached)
            response["cached"] = True
            return response
        except ValueError:
            pass

    if entity["type"] == "hex":
        built = await build_hex_context(db, entity["id"], None if live else hour, live=live)
        if built is None:
            return {"needs_selection": True, "answer": None, "context_label": None, "entity": entity,
                    "cached": False, "detail": f"Hex {entity['id']} tidak ditemukan pada grid aktivitas."}
        corridor_contexts = built["corridor_contexts"]
        corridors = _merge_contexts(corridor_contexts) if corridor_contexts else None
        context = {
            "subject": entity,
            "data_mode": "live" if live else None,
            "displayed_hour_label": None if live else payload.hour_label,
            "observed_hour": built.get("observed_hour"),
            "hex_cell": built["hex_cell"],
            "corridors": corridors,
        }
        prompt = AUTO_INSIGHT_PROMPT_CORRIDOR if corridors else AUTO_INSIGHT_PROMPT_HEX_ONLY
        label = f"grid Hex {entity['id']}"
        if payload.hour_label and not live:
            label += f" · {payload.hour_label}"
        if corridors:
            label += f" · {corridors['segment']['name']}"
    elif entity["type"] == "stop":
        built = await build_stop_context(db, entity["id"])
        if built is None:
            return {"needs_selection": True, "answer": None, "context_label": None, "entity": entity,
                    "cached": False, "detail": f"Halte '{entity['id']}' tidak ditemukan."}
        context = built
        prompt = AUTO_INSIGHT_PROMPT_STOP
        label = f"{built['stop']['title']} ({entity['id']})"
    else:
        ids, _ = await _entity_segment_ids(db, payload)
        contexts = [context for context in [await build_context(db, sid) for sid in ids] if context]
        if not contexts:
            return {"needs_selection": True, "answer": None, "context_label": None, "entity": entity,
                    "cached": False, "detail": "Entitas ini belum memiliki konteks segmen."}
        context = {"subject": entity, **_merge_contexts(contexts)}
        prompt = AUTO_INSIGHT_PROMPT
        chunk_count = context["segment"]["chunk_count"]
        label = (f"{context['segment']['name']} ({chunk_count} segmen)" if chunk_count > 1
                 else f"{context['segment']['name']} ({ids[0]})")

    try:
        answer = await _ask_llm(prompt, context, [], style="intervention")
    except BangJoLLMError as exc:
        logger.warning("bangjo_llm_unavailable", extra={"reason": exc.reason, "source": "auto_insight"})
        raise HTTPException(status_code=502, detail=f"Maaf, Bang Jo tidak dapat dihubungi ({exc.reason}). Coba lagi.")
    response = {"needs_selection": False, "answer": answer, "context_label": label,
                "entity": entity, "cached": False}
    await _cache_set(cache_key, json.dumps(response), settings.BANGJO_AUTOINSIGHT_TTL_SECONDS)
    return response
