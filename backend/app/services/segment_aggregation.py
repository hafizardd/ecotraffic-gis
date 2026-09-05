"""Aggregate interval observations into segment-level traffic counts."""

from collections import defaultdict
from dataclasses import dataclass
from collections.abc import Iterable

from app.services.segment_observation import SegmentTrafficObservation
from cv.proposal_emission_factors import VEHICLE_CATEGORIES


class SegmentAggregationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SegmentAggregation:
    road_segment_id: str
    period_start: object
    period_end: object
    raw_counts: dict[str, float]
    source_cameras: tuple[str, ...]
    source_streams: tuple[str, ...]
    observation_count: int
    aggregation_policy: str
    observation_duration_seconds: float
    vehicle_count_semantics: str


def aggregate_segment_observations(
    observations: Iterable[SegmentTrafficObservation],
    *,
    period_start,
    period_end,
    aggregation_policy: str = "sum_independent_streams",
) -> SegmentAggregation:
    observations = [item for item in observations if period_start <= item.captured_at < period_end]
    if not observations:
        raise SegmentAggregationError("no observations in calculation period")
    segment_ids = {item.road_segment_id for item in observations}
    if len(segment_ids) != 1:
        raise SegmentAggregationError("observations must belong to one road segment")
    if aggregation_policy not in {"sum_independent_streams", "authoritative_camera"}:
        raise SegmentAggregationError(f"unsupported aggregation policy: {aggregation_policy}")

    durations = {item.observation_duration_seconds for item in observations}
    if len(durations) != 1:
        raise SegmentAggregationError("observations must use one duration per calculation period")
    semantics = {item.vehicle_count_semantics.value for item in observations}
    if semantics not in ({"interval_count"}, {"vehicles_per_hour"}, {"snapshot_occupancy"}):
        raise SegmentAggregationError("only interval_count, vehicles_per_hour, or snapshot_occupancy observations can be scored")
    if len(semantics) != 1:
        raise SegmentAggregationError("observations must use one count semantics per calculation period")

    by_stream: dict[str, list[SegmentTrafficObservation]] = defaultdict(list)
    for item in observations:
        by_stream[item.lane_or_stream_id].append(item)
    selected = []
    for stream, stream_observations in by_stream.items():
        if len({item.camera_id for item in stream_observations}) > 1:
            if aggregation_policy == "authoritative_camera":
                selected.append(sorted(stream_observations, key=lambda item: item.camera_id)[0])
            else:
                raise SegmentAggregationError(f"duplicate cameras for stream {stream}")
        else:
            selected.extend(stream_observations)

    counts = {category: 0.0 for category in VEHICLE_CATEGORIES}
    if semantics == {"snapshot_occupancy"}:
        # A live frame is a point-in-time occupancy sample, not a new vehicle
        # count for the whole observation window. Average samples per stream
        # before converting the result to an hourly interval estimate.
        stream_totals: dict[str, dict[str, float]] = defaultdict(
            lambda: {category: 0.0 for category in VEHICLE_CATEGORIES}
        )
        stream_counts: dict[str, int] = defaultdict(int)
        for observation in selected:
            stream_counts[observation.lane_or_stream_id] += 1
            for category in VEHICLE_CATEGORIES:
                stream_totals[observation.lane_or_stream_id][category] += observation.raw_detected_count[category]
        for stream, totals in stream_totals.items():
            for category in VEHICLE_CATEGORIES:
                counts[category] += totals[category] / stream_counts[stream]
    else:
        for observation in selected:
            for category in VEHICLE_CATEGORIES:
                counts[category] += observation.raw_detected_count[category]
    return SegmentAggregation(
        road_segment_id=next(iter(segment_ids)),
        period_start=period_start,
        period_end=period_end,
        raw_counts=counts,
        source_cameras=tuple(sorted({item.camera_id for item in selected})),
        source_streams=tuple(sorted({item.lane_or_stream_id for item in selected})),
        observation_count=len(selected),
        aggregation_policy=aggregation_policy,
        observation_duration_seconds=next(iter(durations)),
        vehicle_count_semantics=("interval_count" if semantics == {"snapshot_occupancy"} else next(iter(semantics))),
    )
