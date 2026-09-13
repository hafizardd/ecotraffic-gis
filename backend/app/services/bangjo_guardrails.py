"""Deterministic guardrails for Bang Jo: scope gate + history sanitizer.

No external dependency and no LLM call: this is a heuristic scope filter for an
internal, single-domain dashboard, not an auth boundary. Ambiguous input passes
(fail-open); only clearly off-topic, overlong, or injection-shaped input is
rejected. Any internal error also fails open.
"""

import re

MAX_QUERY_CHARS = 500
MAX_HISTORY_TURNS = 10
MAX_TURN_CHARS = 1000
# Messages shorter than this pass even without a topic keyword, so greetings and
# terse follow-ups are not misclassified as out of scope.
MIN_SCOPE_WORDS = 4

REJECT_MESSAGE = (
    "Maaf, saya hanya bisa membantu pertanyaan seputar lalu lintas, emisi, koridor, "
    "halte, dan intervensi pada dashboard EcoTraffic."
)

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WORDS = re.compile(r"[a-zA-Z]+")

_TOPIC = re.compile(
    r"\b(lalu ?lintas|traffic|emisi|emission|koridor|segmen|segment|seg|kor|halte|bus ?stop|"
    r"asi|avoid|shift|improve|intervensi|dashboard|volume|kendaraan|vkt|polusi|polutan|"
    r"pencemaran|kemacetan|macet|kecepatan|kepadatan|kapasitas|waktu\s*tempuh|transportasi|"
    r"parkir|rute|angkutan|moda|pejalan|sepeda|mobil|motor|bus|"
    r"co2|co\b|nox|so2|sox|pm|pm10|pm2\.?5|hc|"
    r"malioboro|jalan|jl|gang|gg|peta|wilayah|"
    r"aktivitas|activity|potensi|daerah|kawasan|zona|grid|sel|hex|ruas)\b",
    re.IGNORECASE,
)
_GREETING = re.compile(
    r"^\s*(halo|hai|hi|hello|pagi|siang|malam|selamat|terima\s*kasih|makasih|thanks)\b",
    re.IGNORECASE,
)
# Conversational follow-ups ("kalau yang itu?", "kenapa tadi lebih tinggi?") carry
# no topic keyword. They pass when they also point back at something already
# discussed, so off-topic questions still do not slip through.
_FOLLOWUP = re.compile(
    r"\b(kalau|kalo|yang|juga|kok|gimana|bagaimana|kenapa|mengapa|banding|bandingkan|"
    r"dibanding|versus|vs|sama|rinci|detail|jelaskan|terangkan|lanjut|sebelumnya|tadi)\b",
    re.IGNORECASE,
)
_REFERENTIAL = re.compile(
    r"\b(itu|ini|tersebut|tadi|sebelumnya|lain|lainnya|nya)\b",
    re.IGNORECASE,
)

_INJECTION = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions?|prompts?|rules?)",
        r"abaikan\s+(semua\s+)?(instruksi|perintah|aturan)\s*(sebelumnya|di\s*atas)?",
        r"system\s+prompt",
        r"prompt\s+(sistem|awal)",
        r"reveal\s+(your\s+)?(system|hidden|initial|secret)",
        r"bocorkan\s+(system|prompt|instruksi)",
        r"\byou\s+are\s+(now|no longer)\b",
        r"\bkamu\s+(sekarang\s+)?adalah\b",
        r"<\s*script",
        r"base64",
        r"developer\s+mode",
    )
]


def _injection_match(text: str) -> str | None:
    for pattern in _INJECTION:
        if pattern.search(text):
            return pattern.pattern
    return None


def screen_query(message: str) -> dict:
    """Classify the live query. Returns ``{blocked, reason, message}``.

    Never raises: any unexpected failure is treated as "allow".
    """
    try:
        text = (message or "").strip()
        if not text:
            return {"blocked": True, "reason": "empty", "message": REJECT_MESSAGE}
        if len(text) > MAX_QUERY_CHARS:
            return {"blocked": True, "reason": "too_long", "message": REJECT_MESSAGE}
        if _injection_match(text):
            return {"blocked": True, "reason": "injection", "message": REJECT_MESSAGE}
        in_scope = (
            bool(_TOPIC.search(text))
            or bool(_GREETING.search(text))
            or (bool(_FOLLOWUP.search(text)) and bool(_REFERENTIAL.search(text)))
        )
        if in_scope or len(_WORDS.findall(text)) < MIN_SCOPE_WORDS:
            return {"blocked": False, "reason": None, "message": None}
        return {"blocked": True, "reason": "out_of_scope", "message": REJECT_MESSAGE}
    except Exception:
        return {"blocked": False, "reason": None, "message": None}


def _field(turn, name: str):
    if isinstance(turn, dict):
        return turn.get(name)
    return getattr(turn, name, None)


def sanitize_history(
    history,
    max_turns: int = MAX_HISTORY_TURNS,
    max_chars: int = MAX_TURN_CHARS,
) -> list[dict]:
    """Trust nothing from the client: keep only user/assistant turns, bounded."""
    turns: list[dict] = []
    for turn in history or []:
        role = _field(turn, "role")
        if role not in ("user", "assistant"):
            continue
        content = _CONTROL.sub("", str(_field(turn, "content") or ""))
        for pattern in _INJECTION:
            content = pattern.sub("", content)
        content = content[:max_chars].strip()
        if not content:
            continue
        turns.append({"role": role, "content": content})
    return turns[-max_turns:]
