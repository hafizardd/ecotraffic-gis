"""Classify the age of camera emission data without changing health state."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    fresh_threshold_seconds: int
    aging_threshold_seconds: int

    def __post_init__(self) -> None:
        if self.fresh_threshold_seconds < 0:
            raise ValueError("fresh_threshold_seconds must not be negative")
        if self.aging_threshold_seconds < self.fresh_threshold_seconds:
            raise ValueError(
                "aging_threshold_seconds must be at least fresh_threshold_seconds"
            )

    @classmethod
    def from_settings(cls, settings: Any) -> "FreshnessPolicy":
        return cls(
            fresh_threshold_seconds=settings.DATA_FRESH_THRESHOLD_SECONDS,
            aging_threshold_seconds=settings.DATA_AGING_THRESHOLD_SECONDS,
        )


@dataclass(frozen=True, slots=True)
class Freshness:
    status: FreshnessStatus
    age_seconds: int | None

    def to_payload(self) -> dict[str, str | int | None]:
        return {
            "freshness_status": self.status.value,
            "data_age_seconds": self.age_seconds,
        }


def classify_freshness(
    observed_at: datetime | None,
    *,
    now: datetime,
    policy: FreshnessPolicy,
) -> Freshness:
    if observed_at is None:
        return Freshness(FreshnessStatus.UNKNOWN, None)
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    age_seconds = max(0, int((now - observed_at).total_seconds()))
    if age_seconds <= policy.fresh_threshold_seconds:
        status = FreshnessStatus.FRESH
    elif age_seconds <= policy.aging_threshold_seconds:
        status = FreshnessStatus.AGING
    else:
        status = FreshnessStatus.STALE
    return Freshness(status, age_seconds)


def add_freshness(
    payload: dict[str, Any],
    *,
    observed_at: datetime | None,
    now: datetime,
    policy: FreshnessPolicy,
) -> dict[str, Any]:
    return {**payload, **classify_freshness(observed_at, now=now, policy=policy).to_payload()}


def parse_observed_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)
