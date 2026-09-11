from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .schemas import (
    AccessibilityInfo,
    ConditionInfo,
    EnvironmentInfo,
    FacilitiesInfo,
    Issue,
    SemanticExtraction,
    UsageInfo,
)


JAKARTA = ZoneInfo("Asia/Jakarta")
WORD_SPACE_RE = re.compile(r"\s+")
TIME_RE = re.compile(r"\b(?:sekitar\s+)?(?:pukul|jam)\s*(?P<hour>[01]?\d|2[0-3])[.:](?P<minute>[0-5]\d)\s*(?:WIB)?\b", re.I)
DATE_RE = re.compile(
    r"\b(?P<day>0?[1-9]|[12]\d|3[01])\s+(?P<month>januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+(?P<year>20\d{2})\b",
    re.I,
)
MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}
ACRONYMS = {"TJ", "SMP", "SMPN", "SMA", "SMAN", "SMK", "SD", "UGM", "UNY", "RS", "RSUD", "DIY", "BRI"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".avif"}


def stable_id(prefix: str, *parts: object, length: int = 24) -> str:
    material = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:length]}"


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""
    return WORD_SPACE_RE.sub(" ", unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")).strip()


def normalize_title(value: str | None) -> str:
    text = normalize_whitespace(value)
    words: list[str] = []
    for token in text.split(" "):
        bare = token.strip(".,:;()[]{}")
        if bare.upper() in ACRONYMS:
            words.append(token.replace(bare, bare.upper()))
        elif any(char.isalpha() for char in token):
            words.append(token.lower().capitalize())
        else:
            words.append(token)
    return " ".join(words)


def normalize_stop_name(value: str | None) -> str:
    text = normalize_whitespace(value).casefold()
    text = re.sub(r"#[\w-]+", "", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return normalize_whitespace(text)


def extract_stop_name(title: str | None, description: str | None) -> tuple[str | None, str | None, str | None]:
    raw_title = normalize_whitespace(title)
    if re.search(r"\b(halte|terminal|stop)\b", raw_title, re.I):
        display = normalize_title(raw_title)
        return display, raw_title, normalize_stop_name(display)
    match = re.search(r"\b((?:halte|terminal|stop)\s+[\w .'-]{2,80})", description or "", re.I)
    if not match:
        return None, None, None
    raw = normalize_whitespace(match.group(1)).rstrip(".,")
    display = normalize_title(raw)
    return display, raw, normalize_stop_name(display)


def parse_coordinates(raw: object) -> tuple[float | None, float | None, bool, str | None]:
    try:
        coords = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            raise ValueError("coordinate value is not a two-item array")
        longitude, latitude = float(coords[0]), float(coords[1])
        if not (math.isfinite(longitude) and math.isfinite(latitude)):
            raise ValueError("coordinates must be finite")
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise ValueError("coordinates are outside WGS84 bounds")
        return longitude, latitude, True, None
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, None, False, str(exc)


def parse_created_at(raw: str | None) -> tuple[datetime | None, datetime | None, str | None]:
    if not raw or not raw.strip():
        return None, None, "missing timestamp"
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        utc_value = parsed.astimezone(timezone.utc)
        return utc_value, utc_value.astimezone(JAKARTA), None
    except ValueError as exc:
        return None, None, str(exc)


def time_period_for(value: time | datetime | None) -> str | None:
    if value is None:
        return None
    hour = value.hour
    if 4 <= hour < 7:
        return "early_morning"
    if 7 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "midday"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def extract_observation_time(
    description: str | None,
    *,
    created_at_local: datetime | None = None,
    use_created_at_fallback: bool = False,
) -> dict[str, object]:
    text = description or ""
    time_match = TIME_RE.search(text)
    date_match = DATE_RE.search(text)
    observed_time = None
    observed_date = None
    if time_match:
        observed_time = time(int(time_match.group("hour")), int(time_match.group("minute")))
    if date_match:
        observed_date = date(
            int(date_match.group("year")), MONTHS[date_match.group("month").casefold()], int(date_match.group("day"))
        )

    if observed_time and observed_date:
        observed_at = datetime.combine(observed_date, observed_time, tzinfo=JAKARTA)
        source, confidence = "description_explicit_datetime", 0.98
    elif observed_time:
        observed_at = None
        source, confidence = "description_explicit_time", 0.92
    elif use_created_at_fallback and created_at_local:
        observed_date = created_at_local.date()
        observed_time = created_at_local.timetz().replace(tzinfo=None)
        observed_at = created_at_local
        source, confidence = "created_at_fallback", 0.35
    else:
        observed_at = None
        source, confidence = None, 0.0

    return {
        "observed_date": observed_date,
        "observed_time": observed_time,
        "observed_at": observed_at,
        "observed_time_source": source,
        "observed_time_confidence": confidence,
        "day_of_week": observed_at.strftime("%A").lower() if observed_at else None,
        "time_period": time_period_for(observed_time),
    }


def parse_media(raw: object) -> dict[str, object]:
    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(values, list):
            raise ValueError("media must be a JSON array")
        if any(not isinstance(item, str) for item in values):
            raise ValueError("every media item must be a URL string")
        invalid_urls = [item for item in values if urlparse(item).scheme not in {"http", "https"}]
        if invalid_urls:
            raise ValueError("media contains a non-http(s) URL")
        images, videos = [], []
        for item in values:
            suffix = Path(urlparse(item).path).suffix.casefold()
            if suffix in VIDEO_EXTENSIONS:
                videos.append(item)
            elif suffix in IMAGE_EXTENSIONS:
                images.append(item)
            else:
                images.append(item)
        return {
            "image_urls": images, "video_urls": videos,
            "image_count": len(images), "video_count": len(videos),
            "media_valid": True, "media_error": None,
        }
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "image_urls": [], "video_urls": [], "image_count": 0, "video_count": 0,
            "media_valid": False, "media_error": str(exc),
        }


def haversine_m(a_lon: float, a_lat: float, b_lon: float, b_lat: float) -> float:
    radius_m = 6_371_008.8
    a_lat_r, b_lat_r = math.radians(a_lat), math.radians(b_lat)
    delta_lat = b_lat_r - a_lat_r
    delta_lon = math.radians(b_lon - a_lon)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(a_lat_r) * math.cos(b_lat_r) * math.sin(delta_lon / 2) ** 2
    return 2 * radius_m * math.asin(math.sqrt(value))


def resolve_stop_entities(rows: list[dict[str, object]], *, distance_threshold_m: float = 150.0) -> None:
    """Mutate cleaned rows with deterministic, distance-aware stop identities."""
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        name, raw, normalized = extract_stop_name(str(row.get("title_raw") or ""), str(row.get("description_raw") or ""))
        row.update({"stop_name": name, "stop_name_raw": raw, "stop_name_normalized": normalized})
        if normalized:
            groups[normalized].append(row)

    for normalized_name, candidates in groups.items():
        clusters: list[list[dict[str, object]]] = []
        for row in sorted(candidates, key=lambda item: str(item["observation_id"])):
            if not row.get("coordinates_valid"):
                clusters.append([row])
                continue
            matching = None
            for cluster in clusters:
                valid = [item for item in cluster if item.get("coordinates_valid")]
                if valid and min(
                    haversine_m(float(row["longitude"]), float(row["latitude"]), float(item["longitude"]), float(item["latitude"]))
                    for item in valid
                ) <= distance_threshold_m:
                    matching = cluster
                    break
            (matching if matching is not None else clusters.append([row]))
            if matching is None:
                continue
            matching.append(row)

        multiple_locations = len(clusters) > 1
        for cluster in clusters:
            valid = [row for row in cluster if row.get("coordinates_valid")]
            if valid:
                centroid_lon = sum(float(row["longitude"]) for row in valid) / len(valid)
                centroid_lat = sum(float(row["latitude"]) for row in valid) / len(valid)
                location_key = f"{centroid_lon:.4f},{centroid_lat:.4f}"
                confidence = 0.84 if multiple_locations else (0.95 if len(cluster) > 1 else 0.9)
            else:
                location_key = "coordinates-unavailable"
                confidence = 0.45
            stop_id = stable_id("stop", normalized_name, location_key)
            if multiple_locations:
                status = "split_same_name_distant_coordinates"
            elif len(cluster) > 1:
                status = "resolved_same_name_nearby"
            elif valid:
                status = "resolved_unique"
            else:
                status = "unresolved_missing_coordinates"
            for row in cluster:
                row.update({
                    "stop_id": stop_id,
                    "entity_resolution_confidence": confidence,
                    "entity_resolution_status": status,
                })

    for row in rows:
        if not row.get("stop_name_normalized"):
            row.update({
                "stop_id": None,
                "entity_resolution_confidence": 0.0,
                "entity_resolution_status": "unresolved_missing_stop_name",
            })


def mark_duplicates(rows: list[dict[str, object]]) -> None:
    by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_content: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_source[str(row.get("source_activity_id") or "")].append(row)
        content_hash = hashlib.sha256(str(row.get("description_normalized") or "").casefold().encode("utf-8")).hexdigest()
        row["description_hash"] = content_hash
        by_content[content_hash].append(row)

    for row in rows:
        source_group = by_source[str(row.get("source_activity_id") or "")]
        content_group = by_content[str(row["description_hash"])]
        if len(source_group) > 1:
            material = "|".join(sorted(str(item["observation_id"]) for item in source_group))
            row.update({"duplicate_group_id": stable_id("dup", "source", material), "duplicate_status": "duplicate_source_id"})
        elif len(content_group) > 1:
            row.update({"duplicate_group_id": stable_id("dup", "content", row["description_hash"]), "duplicate_status": "content_duplicate"})
        else:
            row.update({"duplicate_group_id": None, "duplicate_status": "unique"})


def _sentence_with(text: str, needle: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if needle.casefold() in sentence.casefold():
            return sentence.strip()[:280]
    return text.strip()[:280]


def _explicit_boolean(
    text: str,
    terms: tuple[str, ...],
    *,
    mention_is_positive: bool = False,
) -> tuple[bool | None, str | None, float | None]:
    lower = text.casefold()
    for term in terms:
        escaped = re.escape(term.casefold())
        negative = re.search(rf"\b(?:tidak|tanpa|belum)\s+(?:terdapat\s+|memiliki\s+|ada\s+)?{escaped}\b", lower)
        if negative:
            return False, _sentence_with(text, term), 0.92
    for term in terms:
        escaped = re.escape(term.casefold())
        positive = re.search(
            rf"\b(?:terdapat|tersedia|memiliki|dilengkapi(?:\s+dengan)?|ada|terlihat|disediakan)\b[^.!?]{{0,55}}\b{escaped}\b"
            rf"|\b{escaped}\b[^.!?]{{0,35}}\b(?:tersedia|ada|baik|berfungsi|memadai|menyala|terawat|berjaga)\b",
            lower,
        )
        if positive or (mention_is_positive and term.casefold() in lower):
            return True, _sentence_with(text, term), 0.88 if positive else 0.82
    return None, None, None


def deterministic_semantic(description: str) -> SemanticExtraction:
    text = normalize_whitespace(description)
    lower = text.casefold()
    evidence: dict[str, str] = {}
    confidence: dict[str, float] = {}

    count = None
    count_match = re.search(r"\b(?:sekitar\s+)?(\d{1,3})\s+(?:orang|penumpang|pengguna)\b", lower)
    if count_match:
        count = int(count_match.group(1))
        evidence["usage.passenger_count"] = _sentence_with(text, count_match.group(0))
        confidence["usage.passenger_count"] = 0.96

    passenger_level = "unknown"
    passenger_patterns = (
        (r"\b(?:sangat|amat)\s+ramai\b", "very_high", 0.93),
        (r"\b(?:tidak\s+(?:terlihat\s+)?(?:adanya\s+)?penumpang|sepi)\b", "very_low", 0.92),
        (r"\b(?:tidak\s+terlalu\s+ramai|sedikit\s+aktivitas\s+penumpang)\b", "low", 0.9),
        (r"\b(?:cukup\s+ramai|ramai)\b", "high", 0.88),
    )
    for pattern, value, score in passenger_patterns:
        match = re.search(pattern, lower)
        if match:
            passenger_level = value
            evidence["usage.passenger_level"] = _sentence_with(text, match.group(0))
            confidence["usage.passenger_level"] = score
            break

    bus_present, bus_evidence, bus_confidence = _explicit_boolean(text, ("bus trans jogja", "bus"))
    bus_presence_match = re.search(r"\bbus(?:\s+trans\s+jogja)?\b[^.!?]{0,45}\b(?:berhenti|datang|melintas|menjemput)\b", lower)
    if bus_presence_match:
        bus_present = True
        bus_evidence = _sentence_with(text, bus_presence_match.group(0))
        bus_confidence = 0.94
    if bus_present is not None:
        evidence["usage.bus_present"] = bus_evidence or ""
        confidence["usage.bus_present"] = bus_confidence or 0.0

    boarding = None
    boarding_match = re.search(
        r"\b(?:aktivitas\s+(?:naik|turun|naik\s+dan\s+turun)\s+penumpang[^.!?]{0,35}(?:terlihat|aktif|berlangsung)"
        r"|penumpang\s+(?:sedang\s+)?(?:naik|turun)|(?:menjemput|menurunkan)\s+penumpang)\b",
        lower,
    )
    if boarding_match:
        boarding = True
        evidence["usage.boarding_activity"] = _sentence_with(text, boarding_match.group(0))
        confidence["usage.boarding_activity"] = 0.86

    traffic_activity = "unknown"
    traffic_match = re.search(r"lalu\s+lintas\s+(?:yang\s+)?(?:cukup\s+)?(aktif|ramai|padat|sepi)", lower)
    if traffic_match:
        traffic_activity = {"aktif": "high", "ramai": "high", "padat": "very_high", "sepi": "low"}[traffic_match.group(1)]
        evidence["usage.traffic_activity"] = _sentence_with(text, traffic_match.group(0))
        confidence["usage.traffic_activity"] = 0.84

    facility_terms = {
        "has_seating": ("bangku", "tempat duduk"),
        "has_roof": ("atap",),
        "has_shelter": ("shelter",),
        "has_route_information": ("informasi rute", "peta rute"),
        "has_signage": ("rambu halte", "papan halte"),
        "has_staff": ("petugas",),
        "has_lighting": ("lampu halte", "penerangan"),
        "has_fan": ("kipas",),
        "has_water_facility": ("air minum", "fasilitas air"),
        "has_bicycle_parking": ("parkir sepeda",),
        "has_motorcycle_parking": ("parkir motor",),
        "has_wifi": ("wifi", "wi-fi"),
        "has_ticket_counter": ("loket tiket",),
        "has_zebra_crossing": ("zebra cross", "zebra crossing"),
        "has_trash_bin": ("tempat sampah",),
    }
    facility_values: dict[str, object] = {}
    for field, terms in facility_terms.items():
        value, excerpt, score = _explicit_boolean(text, terms)
        facility_values[field] = value
        if value is not None:
            evidence[f"facilities.{field}"] = excerpt or ""
            confidence[f"facilities.{field}"] = score or 0.0

    wheelchair, excerpt, score = _explicit_boolean(
        text, ("ramah kursi roda", "akses kursi roda"), mention_is_positive=True
    )
    if wheelchair is not None:
        evidence["accessibility.wheelchair_access"] = excerpt or ""
        confidence["accessibility.wheelchair_access"] = score or 0.0
    ramp, excerpt, score = _explicit_boolean(text, ("ramp", "jalur landai"))
    if ramp is not None:
        evidence["accessibility.ramp_available"] = excerpt or ""
        confidence["accessibility.ramp_available"] = score or 0.0

    vandalism = None
    issues: list[Issue] = []
    vandalism_match = re.search(r"\b(?:vandalisme|coret(?:an|²|-coret)?)\b", lower)
    vandalism_absent = re.search(r"\b(?:tanpa|bebas|tidak\s+ada)\s+(?:tanda\s+)?(?:vandalisme|coret(?:an|²|-coret)?)\b", lower)
    if vandalism_absent:
        vandalism = False
        excerpt = _sentence_with(text, vandalism_absent.group(0))
        evidence["condition.vandalism"] = excerpt
        confidence["condition.vandalism"] = 0.94
    elif vandalism_match:
        vandalism = True
        excerpt = _sentence_with(text, vandalism_match.group(0))
        evidence["condition.vandalism"] = excerpt
        confidence["condition.vandalism"] = 0.96
        issues.append(Issue(category="maintenance", issue="vandalism", severity="unknown", evidence=excerpt, confidence=0.94))

    nearby_places: list[str] = []
    nearby_categories: list[str] = []
    school_match = re.search(
        r"\b(?:depan|sebelah|dekat)\s+((?:SMPN?|SMAN?|SMK|SDN?)\s+\d+(?:\s+[\w'-]+)*?)"
        r"(?=\s+(?:dan|yang|pada|dengan|serta|karena|untuk|di)\b|[.,]|$)",
        text,
        re.I,
    )
    if school_match:
        place = normalize_whitespace(school_match.group(1)).rstrip(".,")
        nearby_places.append(place)
        nearby_categories.append("school")
        place_evidence = _sentence_with(text, school_match.group(0))
        evidence["environment.nearby_places"] = place_evidence
        evidence["environment.nearby_place_categories"] = place_evidence
        confidence["environment.nearby_places"] = 0.94
        confidence["environment.nearby_place_categories"] = 0.92

    usage = UsageInfo(
        passenger_count=count,
        passenger_level=passenger_level,
        boarding_activity=boarding,
        bus_present=bus_present,
        traffic_activity=traffic_activity,
    )
    facilities = FacilitiesInfo(**facility_values)
    accessibility = AccessibilityInfo(wheelchair_access=wheelchair, ramp_available=ramp)
    condition = ConditionInfo(vandalism=vandalism)
    environment = EnvironmentInfo(nearby_places=nearby_places, nearby_place_categories=nearby_categories)

    result = SemanticExtraction(
        usage=usage,
        facilities=facilities,
        accessibility=accessibility,
        condition=condition,
        environment=environment,
        issues=issues,
        evidence=evidence,
        confidence=confidence,
    )
    return result.model_copy(update={"recommendation_tags": derive_recommendation_tags(result)})


def derive_recommendation_tags(value: SemanticExtraction) -> list[str]:
    tags: list[str] = []
    if value.accessibility.wheelchair_access is True:
        tags.append("wheelchair_friendly")
    if value.accessibility.pedestrian_access == "good":
        tags.append("good_pedestrian_access")
    if value.usage.passenger_level in {"high", "very_high"}:
        tags.append("high_passenger_activity")
    if "school" in value.environment.nearby_place_categories:
        tags.append("near_school")
    if "tourism" in value.environment.nearby_place_categories:
        tags.append("near_tourism_area")
    if value.condition.maintenance in {"excellent", "good"}:
        tags.append("well_maintained")
    if value.condition.lighting_condition in {"poor", "very_poor"}:
        tags.append("poor_lighting")
    if value.condition.cleanliness in {"poor", "very_poor"}:
        tags.append("poor_cleanliness")
    if value.facilities.has_seating is False:
        tags.append("insufficient_seating")
    if value.accessibility.sidewalk_condition in {"poor"}:
        tags.append("sidewalk_obstruction")
    if value.condition.vandalism is True:
        tags.append("vandalism_risk")
    return tags


def normalize_semantic_evidence(value: SemanticExtraction) -> SemanticExtraction:
    """Reset unsupported LLM fields without weakening evidence validation.

    This function is intended for untrusted semantic enrichment before it is
    merged with deterministic extraction.  It never creates evidence and does
    not inspect or modify issues, which carry their own required evidence.
    """

    def meaningful(field_value: object) -> bool:
        return field_value not in (None, "unknown", [], {})

    evidence = {
        key: excerpt
        for key, excerpt in value.evidence.items()
        if excerpt.strip()
    }
    data = value.model_dump(mode="python")
    defaults = SemanticExtraction().model_dump(mode="python")

    for section in ("usage", "facilities", "accessibility", "condition", "environment"):
        for field, field_value in data[section].items():
            evidence_key = f"{section}.{field}"
            if meaningful(field_value) and evidence_key not in evidence:
                data[section][field] = defaults[section][field]

    for field in ("strengths", "weaknesses"):
        has_evidence = any(key == field or key.startswith(f"{field}.") for key in evidence)
        if data[field] and not has_evidence:
            data[field] = defaults[field]

    data["evidence"] = evidence
    data["confidence"] = {
        key: score for key, score in value.confidence.items() if key in evidence
    }
    return SemanticExtraction.model_validate(data)


def merge_semantic(base: SemanticExtraction, enrichment: SemanticExtraction) -> SemanticExtraction:
    def meaningful(value: object) -> bool:
        return value is not None and value != "unknown" and value != [] and value != {}

    def merge(base_value: object, new_value: object) -> object:
        if isinstance(base_value, dict) and isinstance(new_value, dict):
            keys = set(base_value) | set(new_value)
            return {key: merge(base_value.get(key), new_value.get(key)) for key in keys}
        if isinstance(base_value, list) and isinstance(new_value, list):
            result: list[object] = []
            seen: set[str] = set()
            for item in base_value + new_value:
                key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            return result
        return base_value if meaningful(base_value) else new_value

    base_data = base.model_dump(mode="json")
    new_data = enrichment.model_dump(mode="json")
    merged = merge(base_data, new_data)
    merged["evidence"] = {**new_data.get("evidence", {}), **base_data.get("evidence", {})}
    merged["confidence"] = {**new_data.get("confidence", {}), **base_data.get("confidence", {})}
    # Tags are a deterministic projection of validated facts, never free-form LLM recommendations.
    merged["recommendation_tags"] = []
    result = SemanticExtraction.model_validate(merged)
    return result.model_copy(update={"recommendation_tags": derive_recommendation_tags(result)})


def semantic_validation_warnings(value: SemanticExtraction) -> list[str]:
    warnings: list[str] = []
    data = value.model_dump(mode="python")
    for section in ("usage", "facilities", "accessibility", "condition"):
        for field, field_value in data[section].items():
            if field_value not in (None, "unknown", [], {}) and f"{section}.{field}" not in value.evidence:
                warnings.append(f"missing evidence for {section}.{field}")
    for field, field_value in data["environment"].items():
        if field_value and f"environment.{field}" not in value.evidence:
            warnings.append(f"missing evidence for environment.{field}")
    for field in ("strengths", "weaknesses"):
        if data[field] and not any(key == field or key.startswith(f"{field}.") for key in value.evidence):
            warnings.append(f"missing evidence for {field}")
    if (
        value.usage.passenger_count is not None
        and value.usage.passenger_count > 0
        and value.usage.passenger_level == "very_low"
        and not {"usage.passenger_count", "usage.passenger_level"}.issubset(value.evidence)
    ):
        warnings.append("passenger_count > 0 conflicts with passenger_level=very_low")
    for key in value.confidence:
        if key not in value.evidence:
            warnings.append(f"confidence without evidence for {key}")
    return warnings
