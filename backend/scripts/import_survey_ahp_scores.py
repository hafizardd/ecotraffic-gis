"""Idempotently import AHP survey scores, checklists and POI tallies per halte.

Follows the ``import_survey_activities.py`` pattern: one row per ``source_id``,
upsert by lookup, no schema surprises. Rows without AHP data keep their existing
keyword scores (graceful degradation).
"""

from app.core.database import get_sync_db
from app.models.spatial_sources import SurveyStopObservation
from app.services.survey_ahp import (
    AHP_WEIGHT_VERSION,
    damage_indicators,
    environment_detail,
    facility_checklist,
    load_records,
    poi_breakdown_survey,
)


def import_survey_ahp_scores() -> dict:
    records, report = load_records()
    inserted = updated = unmatched = 0
    with get_sync_db() as db:
        for record in records:
            stop = db.query(SurveyStopObservation).filter_by(source_id=record["source_id"]).one_or_none()
            if stop is None:
                print(f"no SurveyStopObservation for source_id={record['source_id']} ({record['title']!r})")
                unmatched += 1
                continue
            detail = record["detail"]
            metadata = dict(stop.source_metadata or {})
            metadata["survey_ahp"] = {
                "observer": record.get("observer"),
                "match_distance_m": record.get("match_distance_m"),
                "environment_detail": environment_detail(detail),
            }
            stop.accessibility_score_100 = record["accessibility_score_100"]
            stop.condition_score_100 = record["condition_score_100"]
            stop.environment_score_100 = record["environment_score_100"]
            stop.ahp_total_score = record["ahp_total_score"]
            stop.ahp_rank = record["ahp_rank"]
            stop.ahp_classification = record["ahp_classification"]
            stop.ahp_weight_version = AHP_WEIGHT_VERSION
            stop.facility_checklist = facility_checklist(detail)
            stop.damage_indicators = damage_indicators(detail)
            stop.poi_breakdown_survey = poi_breakdown_survey(detail)
            stop.score_method = "survey-ahp-v1"
            stop.source_metadata = metadata
            updated += 1
    print(f"survey_ahp_scores: inserted={inserted} updated={updated} unmatched={unmatched} "
          f"(reconcile matched={report['matched']})")
    return {"inserted": inserted, "updated": updated, "unmatched": unmatched}


if __name__ == "__main__":
    import_survey_ahp_scores()
