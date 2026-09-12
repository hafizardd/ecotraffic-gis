"""Canonical segment analytics: interval exits -> vehicles/hour -> VKT -> Tier-2.

Rates use measured exposure per independent stream. Temporal analytics average
rate samples per segment and only sum the same pollutant across segments.
Legacy occupancy extrapolation stays explicitly estimated and versioned;
camera live estimates retain their separate fuel-based calculation path.

Decision scoring has moved to the hex activity grid; this pipeline only emits
volume, VKT and emissions.
"""

from datetime import datetime, timezone

from app.services.segment_observation import VehicleCountSemantics
from app.services.segment_aggregation import aggregate_segment_observations
from app.services.traffic_calculator import vkt_by_category
from app.services.tier2_emission_calculator import calculate_tier2_emissions


def calculate_segment_emission(
    observations, *, period_start, period_end, road_length_km,
    control_efficiency=0.0,
):
    aggregation = aggregate_segment_observations(observations, period_start=period_start, period_end=period_end)
    duration = aggregation.observation_duration_seconds
    occupancy = aggregation.vehicle_count_semantics == VehicleCountSemantics.SNAPSHOT_OCCUPANCY.value
    volume = aggregation.volume_per_hour
    vkt = vkt_by_category(volume, road_length_km)
    emissions = calculate_tier2_emissions(vkt, control_efficiency=control_efficiency)
    return {
        "road_segment_id": aggregation.road_segment_id, "period_start": period_start,
        "period_end": period_end, "calculated_at": datetime.now(timezone.utc),
        "raw_counts": aggregation.raw_counts, "observation_duration_seconds": duration,
        "vehicle_count_semantics": aggregation.vehicle_count_semantics,
        "calculation_version": 2,
        "calculation_mode": "live_occupancy_estimate" if occupancy else "flow_based_segment",
        "data_source": "LIVE",
        "observed_at": aggregation.observed_at.isoformat(),
        "calculation_metadata": {
            "stream_durations_seconds": aggregation.stream_durations_seconds,
            "emission_factor_set": "proposal_tier2_g_per_vehicle_km_v1",
            "control_efficiency_percent": control_efficiency,
            "road_length_km": road_length_km,
            "volume_basis": "occupancy_extrapolation" if occupancy else aggregation.vehicle_count_semantics,
            "flow_exit_policy": "roi_exit_or_missing_track_threshold" if not occupancy else None,
        },
        "volume_per_hour": volume,
        "volume_status": "estimated" if occupancy else "calculated",
        "vkt_km_h": vkt, "emissions": emissions,
        "provenance": {
            "source_cameras": aggregation.source_cameras, "source_streams": aggregation.source_streams,
            "source_observation_count": aggregation.observation_count, "aggregation_policy": aggregation.aggregation_policy,
        },
    }
