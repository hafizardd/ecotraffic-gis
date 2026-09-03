"""Five-criterion Transport Emission Decision Score calculation."""

from collections.abc import Mapping, Sequence
import math


CRITERIA = ("K1", "K2", "K3", "K4", "K5")
DIRECT_CRITERIA = ("K1", "K2", "K4", "K5")
PAIRWISE_MATRIX = (
    (1.00, 1.00, 3.00, 5.00, 7.00),
    (1.00, 1.00, 3.00, 5.00, 7.00),
    (0.33, 0.33, 1.00, 3.00, 5.00),
    (0.20, 0.20, 0.33, 1.00, 3.00),
    (0.14, 0.14, 0.20, 0.33, 1.00),
)
RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12}


def calculate_weights(matrix: Sequence[Sequence[float]] = PAIRWISE_MATRIX) -> dict[str, float]:
    _validate_matrix(matrix)
    size = len(matrix)
    columns = [sum(row[column] for row in matrix) for column in range(size)]
    weights = [sum(matrix[row][column] / columns[column] for column in range(size)) / size for row in range(size)]
    total = sum(weights)
    return {criterion: value / total for criterion, value in zip(CRITERIA, weights)}


def validate_ahp_consistency(matrix: Sequence[Sequence[float]] = PAIRWISE_MATRIX) -> dict[str, float | bool]:
    weights = calculate_weights(matrix)
    vector = [sum(row[column] * list(weights.values())[column] for column in range(len(matrix))) for row in matrix]
    ratios = [value / weight for value, weight in zip(vector, weights.values())]
    lambda_max = sum(ratios) / len(ratios)
    ci = (lambda_max - len(matrix)) / (len(matrix) - 1)
    ri = RI[len(matrix)]
    cr = ci / ri if ri else 0.0
    return {"lambda_max": lambda_max, "ci": ci, "ri": ri, "cr": cr, "is_consistent": cr <= 0.10}


def normalize_criteria(
    values: Mapping[str, float],
    ranges: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, float]:
    result = {}
    for criterion in CRITERIA:
        value = float(values[criterion])
        if not math.isfinite(value):
            raise ValueError(f"{criterion} must be finite")
        result[criterion] = value
    for criterion in CRITERIA:
        low, high = (result[criterion], result[criterion]) if ranges is None else ranges[criterion]
        normalized = 0.0 if high == low else (result[criterion] - low) / (high - low)
        result[criterion] = 1.0 - normalized if criterion == "K3" else normalized
    return result


def decision_score(normalized: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    weights = calculate_weights() if weights is None else weights
    score = sum(weights[criterion] * float(normalized[criterion]) for criterion in CRITERIA)
    return min(1.0, max(0.0, score))


def classify_priority(score: float) -> str:
    score = min(1.0, max(0.0, float(score)))
    if score < 0.20: return "Low"
    if score < 0.40: return "Moderate"
    if score < 0.60: return "High"
    if score < 0.80: return "Very High"
    return "Critical"


def _validate_matrix(matrix: Sequence[Sequence[float]]) -> None:
    if len(matrix) != len(CRITERIA) or any(len(row) != len(CRITERIA) for row in matrix):
        raise ValueError("AHP matrix must be a 5x5 square matrix")
    if any(not math.isfinite(float(value)) or value <= 0 for row in matrix for value in row):
        raise ValueError("AHP matrix values must be positive and finite")
