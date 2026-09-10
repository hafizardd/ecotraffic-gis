"""Shared quintile classification.

Reproduces the offline Excel model formula
``CHOOSE(MIN(5, ROUNDUP(ranking * 5 / total, 0)))`` so the hex grid, bus
stops, and any other ranked layer share one definition instead of
re-deriving the ROUNDUP formula in each place.
"""

import math

# Index 1..5 where index 1 is the "most" of whatever is ranked (highest
# potential for the hex grid, highest intervention urgency for bus stops).
CLASSIFICATION_LABELS = ("Sangat Tinggi", "Tinggi", "Sedang", "Rendah", "Sangat Rendah")


def quintile_classify(rank: int, total: int) -> tuple[int, str]:
    """Return ``(tier, label)`` for a 1-based rank over ``total`` items."""
    if total <= 0:
        raise ValueError("total must be positive")
    tier = min(5, max(1, math.ceil(rank * 5 / total)))
    return tier, CLASSIFICATION_LABELS[tier - 1]
