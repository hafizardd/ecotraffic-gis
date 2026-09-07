"""Idempotently import survey stop observations from activities.csv."""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from geoalchemy2.elements import WKTElement

from app.core.database import get_sync_db
from app.models.spatial_sources import SurveyStopObservation
from app.services.spatial_integration import score_survey_description

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "output" / "activities.csv"


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


def import_survey_activities() -> dict:
    inserted = updated = rejected = 0
    with get_sync_db() as db:
        with open(CSV_PATH, encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                source_id = (row.get("id") or "").strip()
                if not source_id:
                    rejected += 1
                    continue
                coords = _parse_coordinates(row.get("geometry.coordinates"))
                if coords is None:
                    print(f"invalid coordinates for source_id={source_id}", file=sys.stderr)
                    rejected += 1
                    continue
                lon, lat = coords
                existing = db.query(SurveyStopObservation).filter_by(source_id=source_id).one_or_none()
                media = row.get("medias")
                try:
                    media_list = json.loads(media) if media else []
                except (json.JSONDecodeError, TypeError):
                    media_list = []
                evidence = score_survey_description(row.get("description"))
                values = {
                    "title": (row.get("title") or source_id).strip(),
                    "description": row.get("description"),
                    "geometry": WKTElement(f"POINT({lon} {lat})", srid=4326),
                    "media": media_list,
                    "observed_at": _parse_timestamp(row.get("created_at")),
                    "observer_name": row.get("observer") or row.get("observer_name"),
                    "facility_score": evidence["facility"],
                    "pedestrian_access_score": evidence["pedestrian_access"],
                    "environment_score": evidence["environment"],
                    "user_activity_score": evidence["user_activity"],
                    "score_method": "survey-keyword-v1",
                    "source_metadata": {"source_file": "activities.csv", "original_row": row},
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
