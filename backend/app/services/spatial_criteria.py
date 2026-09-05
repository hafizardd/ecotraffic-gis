"""Normalize supplied spatial criterion data without inventing missing values."""

from collections.abc import Mapping, Sequence


SPATIAL_CRITERIA = ("K3", "K4", "K5")


def derive_spatial_criteria(
    segment_values: Sequence[Mapping[str, float | None]],
    *,
    source: str,
    units: Mapping[str, str],
    buffer_distance_m: float | None = None,
    calculation_date: str | None = None,
) -> list[dict]:
    """Return normalized spatial values and provenance for a scoring run."""
    if not source or any(criterion not in units for criterion in SPATIAL_CRITERIA):
        raise ValueError("source and units for K3-K5 are required")
    for row in segment_values:
        missing = [criterion for criterion in SPATIAL_CRITERIA if row.get(criterion) is None]
        if missing:
            raise ValueError(f"missing spatial criteria: {missing}")
    ranges = {
        criterion: (
            min(float(row[criterion]) for row in segment_values),
            max(float(row[criterion]) for row in segment_values),
        )
        for criterion in SPATIAL_CRITERIA
    }
    result = []
    for row in segment_values:
        normalized = {
            criterion: 0.0 if ranges[criterion][0] == ranges[criterion][1] else (float(row[criterion]) - ranges[criterion][0]) / (ranges[criterion][1] - ranges[criterion][0])
            for criterion in SPATIAL_CRITERIA
        }
        normalized["K3"] = 1.0 - normalized["K3"]
        result.append({
            "raw": {criterion: float(row[criterion]) for criterion in SPATIAL_CRITERIA},
            "normalized": normalized,
            "metadata": {"source": source, "units": dict(units), "buffer_distance_m": buffer_distance_m, "calculation_date": calculation_date},
        })
    return result
