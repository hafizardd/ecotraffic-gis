"""Per-bus-stop accessibility + 5-tier intervention classification.

Accessibility is POI count within K4_BUFFER_M of the stop (new for stops;
previously only computed around road segments). It is combined equally with
the survey facility and environment scores — deliberately NOT the segment K3
formula, which mixes different inputs. Set ``BUS_STOP_COMPONENT_WEIGHTS`` to a
new AHP model when the domain team supplies one.
"""

from sqlalchemy import select

from app.models.spatial_sources import SurveyStopObservation
from app.services.classification import quintile_classify
from app.services.spatial_integration import compute_stop_accessibility

BUS_STOP_COMPONENT_WEIGHTS = {"accessibility": 1 / 3, "facility": 1 / 3, "environment": 1 / 3}


def _min_max(values: dict) -> tuple[float, float]:
    present = [value for value in values.values() if value is not None]
    return (min(present), max(present)) if present else (0.0, 0.0)


def build_assessments(stops: list, accessibility: dict) -> list[dict]:
    """Pure scoring pass: accessibility dict maps stop.source_id -> weighted score."""
    low, high = _min_max(accessibility)
    normalized = {
        source_id: (0.0 if high == low else (value - low) / (high - low))
        for source_id, value in accessibility.items()
    }
    assessments = []
    for stop in stops:
        components = {name: None for name in BUS_STOP_COMPONENT_WEIGHTS}
        if stop.source_id in normalized:
            components["accessibility"] = normalized[stop.source_id]
        if stop.facility_score is not None:
            components["facility"] = stop.facility_score / 5.0
        if stop.environment_score is not None:
            components["environment"] = stop.environment_score / 5.0
        available = [value for value in components.values() if value is not None]
        composite = sum(available) / len(available) if available else None
        assessments.append({"source_id": stop.source_id, "components": components, "score": composite})
    ranked = sorted((a for a in assessments if a["score"] is not None), key=lambda a: a["score"], reverse=True)
    total = len(ranked)
    for position, assessment in enumerate(ranked, start=1):
        _, assessment["class"] = quintile_classify(position, total)
        assessment["rank"] = position
    return assessments


def score_bus_stops(db) -> dict:
    stops = db.execute(select(SurveyStopObservation)).scalars().all()
    accessibility = {stop.source_id: compute_stop_accessibility(db, stop)["weighted_score"] for stop in stops}
    assessments = {a["source_id"]: a for a in build_assessments(stops, accessibility)}
    scored = 0
    for stop in stops:
        assessment = assessments[stop.source_id]
        stop.accessibility_score = accessibility.get(stop.source_id)
        stop.intervention_score = assessment["score"]
        stop.intervention_rank = assessment.get("rank")
        stop.intervention_class = assessment.get("class")
        if assessment["score"] is not None:
            scored += 1
    db.commit()
    return {"total": len(stops), "scored": scored}
