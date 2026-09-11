"""Per-bus-stop accessibility + 5-tier intervention classification.

Two scoring paths:

* **AHP (authoritative).** Stops imported from the offline survey workbook carry
  ``ahp_total_score``/``ahp_classification`` computed with the validated Saaty
  weights (Aksesibilitas 0.4111, Kondisi 0.3278, Lingkungan 0.2611, CR = 0.048).
  Those values are used directly — the survey team's accessibility score is
  trusted over the live POI join, which stays for the panel's informational
  "POI sekitar" breakdown.
* **Keyword fallback.** Any stop without AHP data (e.g. a future lighter-weight
  survey round) is scored from the live POI accessibility plus the keyword
  facility/environment scores, then quintile-ranked.
"""

from sqlalchemy import select

from app.models.spatial_sources import SurveyStopObservation
from app.services.classification import quintile_classify
from app.services.spatial_integration import compute_stop_accessibility
from app.services.survey_ahp import AHP_WEIGHTS

# Validated AHP weights (workbook "AHP" sheet, CR = 0.048, consistent). The
# fallback path reuses the same priority so mixed corridors stay comparable.
BUS_STOP_COMPONENT_WEIGHTS = {
    "accessibility": AHP_WEIGHTS["accessibility"],
    "facility": AHP_WEIGHTS["condition"],
    "environment": AHP_WEIGHTS["environment"],
}
AHP_COMPONENT_COLUMNS = {
    "accessibility": "accessibility_score_100",
    "condition": "condition_score_100",
    "environment": "environment_score_100",
}


def _min_max(values: dict) -> tuple[float, float]:
    present = [value for value in values.values() if value is not None]
    return (min(present), max(present)) if present else (0.0, 0.0)


def build_assessments(stops: list, accessibility: dict) -> list[dict]:
    """Pure scoring pass: accessibility dict maps stop.source_id -> weighted score.

    AHP-scored stops keep their imported score/class; the rest are
    weighted-composite scored (0-100) and quintile-classified. ``rank`` is an
    intervention-priority rank across every scored stop: the LOWEST score is
    rank 1 (most urgent), the highest score is last.
    """
    low, high = _min_max(accessibility)
    normalized = {
        source_id: (0.0 if high == low else (value - low) / (high - low))
        for source_id, value in accessibility.items()
    }
    assessments = []
    for stop in stops:
        ahp_total = getattr(stop, "ahp_total_score", None)
        if ahp_total is not None:
            components = {
                name: (getattr(stop, column, None) / 100 if getattr(stop, column, None) is not None else None)
                for name, column in AHP_COMPONENT_COLUMNS.items()
            }
            assessments.append({
                "source_id": stop.source_id, "components": components, "score": ahp_total,
                "class": getattr(stop, "ahp_classification", None), "rank": None,
                "method": "ahp",
            })
            continue
        components = {name: None for name in BUS_STOP_COMPONENT_WEIGHTS}
        if stop.source_id in normalized:
            components["accessibility"] = normalized[stop.source_id]
        if stop.facility_score is not None:
            components["facility"] = stop.facility_score / 5.0
        if stop.environment_score is not None:
            components["environment"] = stop.environment_score / 5.0
        available = [(BUS_STOP_COMPONENT_WEIGHTS[name], value) for name, value in components.items() if value is not None]
        weight_sum = sum(weight for weight, _ in available)
        composite = (sum(weight * value for weight, value in available) / weight_sum * 100) if weight_sum else None
        assessments.append({
            "source_id": stop.source_id, "components": components, "score": composite,
            "class": None, "rank": None, "method": "keyword",
        })

    fallback = sorted(
        (a for a in assessments if a["method"] == "keyword" and a["score"] is not None),
        key=lambda a: a["score"],
        reverse=True,
    )
    total = len(fallback)
    for position, assessment in enumerate(fallback, start=1):
        _, assessment["class"] = quintile_classify(position, total)

    # Intervention priority: lowest score = rank 1 (top priority). AHP stops are
    # re-ranked here too so imported ``ahp_rank`` can't carry the opposite order.
    priority = sorted(
        (a for a in assessments if a["score"] is not None),
        key=lambda a: (a["score"], a["source_id"]),
    )
    for position, assessment in enumerate(priority, start=1):
        assessment["rank"] = position
    return assessments


def score_bus_stops(db) -> dict:
    stops = db.execute(select(SurveyStopObservation)).scalars().all()
    accessibility = {stop.source_id: compute_stop_accessibility(db, stop)["weighted_score"] for stop in stops}
    assessments = {a["source_id"]: a for a in build_assessments(stops, accessibility)}
    scored = 0
    for stop in stops:
        assessment = assessments[stop.source_id]
        stop.accessibility_score = (
            stop.accessibility_score_100 if stop.accessibility_score_100 is not None
            else accessibility.get(stop.source_id)
        )
        stop.intervention_score = assessment["score"]
        stop.intervention_rank = assessment.get("rank")
        stop.intervention_class = assessment.get("class")
        if assessment["score"] is not None:
            scored += 1
    db.commit()
    return {"total": len(stops), "scored": scored}
