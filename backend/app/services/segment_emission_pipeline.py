"""Pure orchestration for one segment calculation period."""

from datetime import datetime, timezone

from app.services.ahp_calculator import calculate_weights, classify_priority, decision_score, normalize_criteria, validate_ahp_consistency
from app.services.segment_aggregation import aggregate_segment_observations
from app.services.traffic_calculator import volume_per_hour, vkt_by_category
from app.services.tier2_emission_calculator import calculate_tier2_emissions


def calculate_segment_emission(
    observations, *, period_start, period_end, road_length_km,
    spatial_criteria=None, criterion_ranges=None, control_efficiency=0.0,
):
    aggregation = aggregate_segment_observations(observations, period_start=period_start, period_end=period_end)
    duration = observations[0].observation_duration_seconds
    volume = volume_per_hour(aggregation.raw_counts, duration)
    vkt = vkt_by_category(volume, road_length_km)
    emissions = calculate_tier2_emissions(vkt, control_efficiency=control_efficiency)
    raw = {
        "K1": sum(emissions["totals_g_h"].values()),
        "K2": sum(volume.values()),
        "K3": None if spatial_criteria is None else spatial_criteria.get("K3"),
        "K4": None if spatial_criteria is None else spatial_criteria.get("K4"),
        "K5": None if spatial_criteria is None else spatial_criteria.get("K5"),
    }
    spatial_pending = any(raw[key] is None for key in ("K3", "K4", "K5"))
    result = {
        "road_segment_id": aggregation.road_segment_id, "period_start": period_start,
        "period_end": period_end, "calculated_at": datetime.now(timezone.utc),
        "raw_counts": aggregation.raw_counts, "volume_per_hour": volume,
        "vkt_km_h": vkt, "emissions": emissions, "raw_criteria": raw,
        "spatial_criteria_status": "pending" if spatial_pending else "complete",
        "provenance": {"source_cameras": aggregation.source_cameras, "source_streams": aggregation.source_streams, "aggregation_policy": aggregation.aggregation_policy},
    }
    if not spatial_pending:
        normalized = normalize_criteria(raw, criterion_ranges)
        weights = calculate_weights()
        consistency = validate_ahp_consistency()
        score = decision_score(normalized, weights)
        result.update({"normalized_criteria": normalized, "ahp_weights": weights, "ahp_consistency": consistency, "decision_score": score, "priority": classify_priority(score)})
    return result
