"""Load and reconcile the offline AHP survey scoring workbook.

Pure file parsing (no DB): used by ``scripts/reconcile_survey_scoring.py`` for
the match report and by ``scripts/import_survey_ahp_scores.py`` for the
idempotent import.

Coordinates are the primary join key: the geojson/``Ringkasan`` export and
``activities.csv`` share the exact same points (0 m offsets in practice) but not
the same titles, and there is no shared numeric id. Title matching is only a
fallback.
"""

import csv
import json
import math
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
GEOJSON_PATH = DATA_DIR / "Perhitungan Hasil Survei.geojson"
XLSX_PATH = DATA_DIR / "Perhitungan Data Survei.xlsx"
ACTIVITIES_CSV_PATH = DATA_DIR / "output" / "activities.csv"

# Validated Saaty pairwise weights from the workbook's "AHP" sheet (CR = 0.048).
AHP_WEIGHTS = {
    "accessibility": 0.41111111111111115,
    "condition": 0.3277777777777778,
    "environment": 0.2611111111111111,
}
AHP_WEIGHT_VERSION = "ahp-halte-v1"
AHP_CONSISTENCY_RATIO = 0.047892720306513245
MATCH_TOLERANCE_M = 25.0

FACILITY_COLUMNS = {
    "atap_shelter": "Ada: atap shelter",
    "tempat_duduk": "Ada: tempat duduk",
    "papan_informasi_rute": "Ada: papan informasi rute",
    "jalur_landai_difabel": "Ada: jalur landai difabel",
    "penerangan": "Ada: penerangan",
    "dinding_kaca_pembatas": "Ada: dinding kaca pembatas",
    "kipas_angin": "Ada: kipas angin",
    "papan_nama": "Ada: papan nama jelas",
}
DAMAGE_COLUMNS = {
    "rusak_robek": "Terdeteksi: rusak robek",
    "vandalisme": "Terdeteksi: coret vandalisme",
    "karat_mengelupas": "Terdeteksi: karat mengelupas",
    "kotor_debu_sampah": "Terdeteksi: kotor debu sampah",
    "akses_terhalang": "Terdeteksi: akses terhalang",
}
POI_CATEGORIES = (
    "Kesehatan", "Kuliner", "Pariwisata", "Pendidikan",
    "Perdagangan", "Peribadatan", "Perkantoran", "Transportasi",
)
FACILITY_COUNT_COLUMN = "Jml Fasilitas Ditemukan"
DAMAGE_COUNT_COLUMN = "Jml Indikator Kerusakan"


def _norm_title(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _clean_title(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _to_float(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    number = _to_float(value)
    return int(number) if number is not None else None


def _is_yes(value) -> bool:
    return str(value or "").strip().casefold() == "ya"


def _haversine_m(lon1, lat1, lon2, lat2) -> float:
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _parse_coordinates(raw) -> tuple[float, float] | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        coords = raw
    else:
        try:
            coords = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    lon, lat = _to_float(coords[0]), _to_float(coords[1])
    if lon is None or lat is None:
        return None
    return lon, lat


def _sheet_rows(worksheet) -> list[dict]:
    """First row is the header; returns one dict per non-empty data row."""
    rows = worksheet.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        return []
    columns = [str(name).strip() if name is not None else "" for name in header]
    records = []
    for row in rows:
        if row is None or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        records.append({columns[index]: row[index] for index in range(min(len(columns), len(row)))})
    return records


def _load_xlsx_details() -> dict[str, dict]:
    import openpyxl  # only the standalone import/reconcile scripts need this

    workbook = openpyxl.load_workbook(XLSX_PATH, data_only=True, read_only=True)
    details: dict[str, dict] = {}
    try:
        akses = {_norm_title(r["Nama Halte"]): r for r in _sheet_rows(workbook["Detail Aksesibilitas"])}
        kondisi = {_norm_title(r["Nama Halte"]): r for r in _sheet_rows(workbook["Detail Kondisi"])}
        lingkungan = {_norm_title(r["Nama Halte"]): r for r in _sheet_rows(workbook["Detail Lingkungan"])}
    finally:
        workbook.close()
    for key in set(akses) | set(kondisi) | set(lingkungan):
        details[key] = {"aksesibilitas": akses.get(key), "kondisi": kondisi.get(key), "lingkungan": lingkungan.get(key)}
    return details


def _load_geojson() -> list[dict]:
    with open(GEOJSON_PATH, encoding="utf-8") as handle:
        collection = json.load(handle)
    stops = []
    for feature in collection.get("features", []):
        props = feature.get("properties") or {}
        lon, lat = _parse_coordinates((feature.get("geometry") or {}).get("coordinates")) or (None, None)
        if lon is None or lat is None:
            lon, lat = _to_float(props.get("Longitude")), _to_float(props.get("Latitude"))
        stops.append({
            "title": _clean_title(props.get("Nama Halte")),
            "observer": props.get("Observer"),
            "accessibility_score_100": _to_float(props.get("Skor Aksesibilitas (0-100)")),
            "condition_score_100": _to_float(props.get("Skor Kondisi (0-100)")),
            "environment_score_100": _to_float(props.get("Skor Lingkungan (0-100)")),
            "ahp_total_score": _to_float(props.get("SKOR TOTAL (AHP) (%)")),
            "ahp_rank": _to_int(props.get("Peringkat")),
            "ahp_classification": props.get("Klasifikasi halte"),
            "longitude": lon,
            "latitude": lat,
        })
    return stops


def _load_activities() -> list[dict]:
    with open(ACTIVITIES_CSV_PATH, encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for raw in reader:
            source_id = (raw.get("id") or "").strip()
            if not source_id:
                continue
            lon, lat = _parse_coordinates(raw.get("geometry.coordinates")) or (None, None)
            rows.append({"source_id": source_id, "title": _clean_title(raw.get("title")), "longitude": lon, "latitude": lat})
    return rows


def _match_by_coordinates(stops: list[dict], activities: list[dict], tolerance_m: float, report: dict):
    usable = [row for row in activities if row["longitude"] is not None and row["latitude"] is not None]
    matched: list[tuple[dict, dict, float]] = []
    used_ids: set[str] = set()
    for stop in stops:
        if stop["longitude"] is None or stop["latitude"] is None:
            report["beyond_tolerance"].append({"title": stop["title"], "reason": "no_geojson_coordinates"})
            continue
        ranked = sorted(
            usable,
            key=lambda row: _haversine_m(stop["longitude"], stop["latitude"], row["longitude"], row["latitude"]),
        )
        if not ranked:
            report["beyond_tolerance"].append({"title": stop["title"], "reason": "no_activities_rows"})
            continue
        nearest = ranked[0]
        distance = _haversine_m(stop["longitude"], stop["latitude"], nearest["longitude"], nearest["latitude"])
        if distance > tolerance_m:
            report["beyond_tolerance"].append(
                {"title": stop["title"], "nearest_source_id": nearest["source_id"], "distance_m": round(distance, 1)}
            )
            continue
        if len(ranked) > 1:
            second = ranked[1]
            second_distance = _haversine_m(stop["longitude"], stop["latitude"], second["longitude"], second["latitude"])
            if second_distance <= tolerance_m:
                report["ambiguous_matches"].append({
                    "title": stop["title"], "source_id": nearest["source_id"],
                    "second_source_id": second["source_id"], "second_distance_m": round(second_distance, 1),
                })
        matched.append((stop, nearest, distance))
        used_ids.add(nearest["source_id"])
    return matched, used_ids


def _match_by_title(stop: dict, activities_by_title: dict[str, dict]) -> dict | None:
    return activities_by_title.get(_norm_title(stop["title"]))


def load_records(tolerance_m: float = MATCH_TOLERANCE_M) -> tuple[list[dict], dict]:
    """Return ``(records, report)`` for every scored halte matched to a source_id."""
    stops = _load_geojson()
    activities = _load_activities()
    details = _load_xlsx_details()
    activities_by_title = {_norm_title(row["title"]): row for row in activities}
    report: dict = {
        "geojson_stops": len(stops), "activities_rows": len(activities),
        "matched": 0, "unmatched_geo": [], "unmatched_csv": [],
        "ambiguous_matches": [], "beyond_tolerance": [],
    }

    matched, used_ids = _match_by_coordinates(stops, activities, tolerance_m, report)

    records = []
    for stop, source, distance in matched:
        detail = details.get(_norm_title(stop["title"]))
        if detail is None:
            report["unmatched_geo"].append({"title": stop["title"], "reason": "no_detail_sheet"})
            continue
        records.append({**stop, "source_id": source["source_id"], "source_title": source["title"],
                        "match_distance_m": round(distance, 3), "detail": detail})

    matched_titles = {record["title"] for record in records}
    matched_ids = {record["source_id"] for record in records}
    for stop in stops:
        if stop["title"] in matched_titles:
            continue
        # coordinate join failed: fall back to exact normalized title
        source = _match_by_title(stop, activities_by_title)
        if source is not None and source["source_id"] not in matched_ids:
            detail = details.get(_norm_title(stop["title"]))
            if detail is not None:
                used_ids.add(source["source_id"])
                records.append({**stop, "source_id": source["source_id"], "source_title": source["title"],
                                "match_distance_m": None, "detail": detail})
                continue
        if not any(item.get("title") == stop["title"] for item in report["beyond_tolerance"]):
            report["unmatched_geo"].append({"title": stop["title"], "reason": "no_source_match"})

    report["matched"] = len(records)
    report["unmatched_csv"] = [
        {
            "source_id": row["source_id"], "title": row["title"],
            "nearest_scored_m": round(min(
                (_haversine_m(stop["longitude"], stop["latitude"], row["longitude"], row["latitude"])
                 for stop in stops if stop["longitude"] is not None),
                default=float("inf"),
            ), 1) if row["longitude"] is not None and row["latitude"] is not None else None,
        }
        for row in activities if row["source_id"] not in used_ids
    ]
    return records, report


def _detail_value(detail: dict, sheet: str, column: str):
    row = detail.get(sheet)
    return row.get(column) if row else None


def facility_checklist(detail: dict) -> dict:
    return {key: _is_yes(_detail_value(detail, "kondisi", column)) for key, column in FACILITY_COLUMNS.items()}


def damage_indicators(detail: dict) -> dict:
    return {key: _is_yes(_detail_value(detail, "kondisi", column)) for key, column in DAMAGE_COLUMNS.items()}


def poi_breakdown_survey(detail: dict) -> dict:
    breakdown = {}
    for category in POI_CATEGORIES:
        count = _to_int(_detail_value(detail, "aksesibilitas", category))
        if count:
            breakdown[category] = count
    return breakdown


def environment_detail(detail: dict) -> dict:
    return {
        "cleanliness_subscore": _to_int(_detail_value(detail, "lingkungan", "Sub-skor Kebersihan (0-100)")),
        "vegetation_mentioned": _is_yes(_detail_value(detail, "lingkungan", "Ada Vegetasi Disebut")),
        "positive_mentions": _to_int(_detail_value(detail, "lingkungan", "Sebutan Positif (bersih/rapi/terawat)")),
        "negative_mentions": _to_int(_detail_value(detail, "lingkungan", "Sebutan Negatif (kotor/sampah/kumuh)")),
    }
