"""Idempotently import standardized survey stop observations."""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from geoalchemy2.elements import WKTElement

from app.core.database import get_sync_db
from app.models.spatial_sources import SurveyStopObservation
from app.services.spatial_integration import score_survey_description

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CLEANED_CSV_PATH = DATA_DIR / "cleaned" / "activities_cleaned.csv"
LEGACY_CSV_PATH = DATA_DIR / "output" / "activities.csv"


def _parse_timestamp(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_coordinates(raw) -> tuple[float, float] | None:
    if not raw:
        return None
    try:
        coords = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


def import_survey_activities(csv_path: Path | None = None) -> dict:
    csv_path = csv_path or (CLEANED_CSV_PATH if CLEANED_CSV_PATH.exists() else LEGACY_CSV_PATH)
    inserted = updated = rejected = 0
    with get_sync_db() as db:
        with open(csv_path, encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                standardized = "source_activity_id" in row
                source_id = (row.get("source_activity_id") or row.get("id") or "").strip()
                if not source_id:
                    rejected += 1
                    continue
                if standardized:
                    try:
                        coords = (float(row["longitude"]), float(row["latitude"])) if row.get("coordinates_valid", "").lower() == "true" else None
                    except (TypeError, ValueError):
                        coords = None
                else:
                    coords = _parse_coordinates(row.get("geometry.coordinates"))
                if coords is None:
                    print(f"invalid coordinates for source_id={source_id}", file=sys.stderr)
                    rejected += 1
                    continue
                lon, lat = coords
                existing = db.query(SurveyStopObservation).filter_by(source_id=source_id).one_or_none()
                if standardized:
                    media_list = []
                    for field in ("image_urls", "video_urls"):
                        try:
                            media_list.extend(json.loads(row.get(field) or "[]"))
                        except (json.JSONDecodeError, TypeError):
                            pass
                    description = row.get("description_raw")
                    title = row.get("title_normalized") or row.get("title_raw") or source_id
                    observed_at = _parse_timestamp(row.get("observed_at"))
                    observer = row.get("user_full_name") or row.get("user_name")
                else:
                    media = row.get("medias")
                    try:
                        media_list = json.loads(media) if media else []
                    except (json.JSONDecodeError, TypeError):
                        media_list = []
                    description = row.get("description")
                    title = (row.get("title") or source_id).strip()
                    # Legacy input only has upload time; do not mislabel it as observation time.
                    observed_at = None
                    observer = row.get("observer") or row.get("observer_name")
                evidence = score_survey_description(description)
                values = {
                    "title": title,
                    "description": description,
                    "geometry": WKTElement(f"POINT({lon} {lat})", srid=4326),
                    "media": media_list,
                    "observed_at": observed_at,
                    "observer_name": observer,
                    "facility_score": evidence["facility"],
                    "pedestrian_access_score": evidence["pedestrian_access"],
                    "environment_score": evidence["environment"],
                    "user_activity_score": evidence["user_activity"],
                    "score_method": "survey-keyword-v1",
                    "source_metadata": {
                        "source_file": row.get("source_file") or csv_path.name,
                        "source_row": row.get("source_row"),
                        "observation_id": row.get("observation_id"),
                        "stop_id": row.get("stop_id"),
                        "created_at_utc": row.get("created_at_utc") or row.get("created_at"),
                        "observed_time_source": row.get("observed_time_source"),
                        "original_row": row,
                    },
                }
                if existing is None:
                    db.add(SurveyStopObservation(source_id=source_id, **values))
                    inserted += 1
                else:
                    for key, value in values.items():
                        setattr(existing, key, value)
                    updated += 1
    print(f"survey_stop_observations: inserted={inserted} updated={updated} rejected={rejected}")
    return {"inserted": inserted, "updated": updated, "rejected": rejected}


if __name__ == "__main__":
    import_survey_activities()
