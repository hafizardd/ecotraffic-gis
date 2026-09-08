"""Pure orchestration for one segment calculation period.

Canonical hourly aggregation logic (live + history share one definition):

per-camera window (60s, epoch-aligned):
  mean_counts[veh] = sum(snapshot_counts) / sample_count
  camera_emission  = calculate_emission(mean_counts)  # fuel-based g/min + kg/hr
  -> 1 EmissionAggregate row / camera / minute

per-segment period (60s, [now-60, now)):
  per-stream mean occupancy = sum(snapshot_occupancy) / n
  raw_counts   = sum over streams
  volume/hr    = raw * 3600/60          # always labeled "estimated"
  vkt          = volume * length_km
  segment_emission = Tier2(vkt)         # proposal factors, g/jam per pollutant
  -> 1 SegmentEmission row / segment / minute

hourly history view (read-only, no new table in v1):
  hour_bucket = date_trunc('hour', period_end)
  hourly_emission_g = avg(totals) per bucket
  hourly_volume     = avg(volume_per_hour) per bucket
  score/priority    = max(decision_score) row per bucket
  (avg, never sum: rows are rate samples; sum would double city totals)
"""

from datetime import datetime, timezone

from app.services.ahp_calculator import aggregate_emission_criterion, calculate_weights, classify_priority, decision_score, normalize_criteria, validate_ahp_consistency
from app.services.segment_observation import VehicleCountSemantics
from app.services.segment_aggregation import aggregate_segment_observations
from app.services.traffic_calculator import volume_per_hour, vkt_by_category
from app.services.tier2_emission_calculator import calculate_tier2_emissions


def calculate_segment_emission(
    observations, *, period_start, period_end, road_length_km,
    spatial_criteria=None, criterion_ranges=None, pollutant_ranges=None,
    control_efficiency=0.0, spatial_details=None,
):
    # Regression guard: no placeholder (e.g. 0.5) K3/K4/K5 path — when spatial
    # is pending, decision_score/priority are omitted, not invented.
    aggregation = aggregate_segment_observations(observations, period_start=period_start, period_end=period_end)
    duration = aggregation.observation_duration_seconds
    occupancy = aggregation.vehicle_count_semantics == VehicleCountSemantics.SNAPSHOT_OCCUPANCY.value
    volume = volume_per_hour(
        aggregation.raw_counts, duration,
        already_hourly=aggregation.vehicle_count_semantics == VehicleCountSemantics.VEHICLES_PER_HOUR.value,
    )
    vkt = vkt_by_category(volume, road_length_km)
    emissions = calculate_tier2_emissions(vkt, control_efficiency=control_efficiency)
    raw = {
        "K1": (
            aggregate_emission_criterion(emissions["totals_g_h"], pollutant_ranges)
            if pollutant_ranges is not None
            else sum(emissions["totals_g_h"].values())
        ),
        "K2": sum(volume.values()),
        "K3": None if spatial_criteria is None else spatial_criteria.get("K3"),
        "K4": None if spatial_criteria is None else spatial_criteria.get("K4"),
        "K5": None if spatial_criteria is None else spatial_criteria.get("K5"),
    }
    spatial_pending = any(raw[key] is None for key in ("K3", "K4", "K5"))
    component_status = {key: ("complete" if raw[key] is not None else "pending") for key in ("K3", "K4", "K5")}
    result = {
        "road_segment_id": aggregation.road_segment_id, "period_start": period_start,
        "period_end": period_end, "calculated_at": datetime.now(timezone.utc),
        "raw_counts": aggregation.raw_counts, "observation_duration_seconds": duration,
        "vehicle_count_semantics": aggregation.vehicle_count_semantics,
        "volume_per_hour": volume,
        "volume_status": "estimated" if occupancy else "calculated",
        "vkt_km_h": vkt, "emissions": emissions, "raw_criteria": raw,
        "normalized_values": spatial_details.get("normalized_values") if spatial_details else None,
        "component_status": component_status,
        "spatial_criteria_status": "pending" if spatial_pending else "complete",
        "spatial_details": spatial_details,
        "provenance": {
            "source_cameras": aggregation.source_cameras, "source_streams": aggregation.source_streams,
            "source_observation_count": aggregation.observation_count, "aggregation_policy": aggregation.aggregation_policy,
            "spatial": spatial_details.get("provenance") if spatial_details else None,
        },
    }
    if not spatial_pending:
        normalized = normalize_criteria(raw, criterion_ranges)
        weights = calculate_weights()
        consistency = validate_ahp_consistency()
        score = decision_score(normalized, weights)
        result.update({"normalized_criteria": normalized, "ahp_weights": weights, "ahp_consistency": consistency, "decision_score": score, "priority": classify_priority(score)})
    return result
