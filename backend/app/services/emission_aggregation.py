from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
import threading
from typing import Any

from cv.emission_factors import calculate_emission
from cv.proposal_emission_factors import normalize_vehicle_counts


VEHICLE_TYPES = ("car", "motorcycle", "bus", "truck")
EMISSION_RATE_FIELDS = (
    "total_tsp_g_per_min",
    "total_tsp_kg_per_hr",
    "total_nox_g_per_min",
    "total_nox_kg_per_hr",
    "total_so2_g_per_min",
    "total_so2_kg_per_hr",
    "total_hc_g_per_min",
    "total_hc_kg_per_hr",
    "total_co_g_per_min",
    "total_co_kg_per_hr",
    "total_co2_g_per_min",
    "total_co2_kg_per_hr",
    "total_ch4_g_per_min",
    "total_ch4_kg_per_hr",
    "total_n2o_g_per_min",
    "total_n2o_kg_per_hr",
)


class LateEmissionObservation(ValueError):
    pass


def _require_aware(timestamp: datetime, field_name: str) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class EmissionObservation:
    camera_id: str
    camera_database_id: str
    job_id: str
    captured_at: datetime
    vehicle_counts: Mapping[str, int | float]
    frame_acquisition_latency_s: float = 0.0
    queue_wait_s: float = 0.0
    inference_latency_s: float = 0.0
    cycle_duration_s: float = 0.0

    def __post_init__(self) -> None:
        _require_aware(self.captured_at, "captured_at")
        normalized_counts = normalize_vehicle_counts(self.vehicle_counts)
        for vehicle_type in VEHICLE_TYPES:
            count = float(normalized_counts.get(vehicle_type, 0))
            if not math.isfinite(count) or count < 0:
                raise ValueError(
                    f"vehicle count for {vehicle_type} must be finite and non-negative"
                )
            normalized_counts[vehicle_type] = count
        object.__setattr__(self, "vehicle_counts", normalized_counts)


@dataclass(frozen=True, slots=True)
class AggregatedEmission:
    camera_id: str
    camera_database_id: str
    period_start: datetime
    period_end: datetime
    last_captured_at: datetime
    sample_count: int
    mean_vehicle_counts: Mapping[str, float]
    emission: Mapping[str, float]
    mean_frame_acquisition_latency_s: float
    mean_queue_wait_s: float
    mean_inference_latency_s: float
    mean_cycle_duration_s: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "camera_database_id": self.camera_database_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "last_captured_at": self.last_captured_at.isoformat(),
            "sample_count": self.sample_count,
            "aggregation_method": "arithmetic_mean_of_snapshot_counts",
            "vehicle_count_semantics": "mean_observed_snapshot_count",
            "vehicle_count": {
                vehicle_type: round(count, 3)
                for vehicle_type, count in self.mean_vehicle_counts.items()
            },
            "emission": dict(self.emission),
            "mean_frame_acquisition_latency_s": round(
                self.mean_frame_acquisition_latency_s,
                3,
            ),
            "mean_queue_wait_s": round(self.mean_queue_wait_s, 3),
            "mean_inference_latency_s": round(
                self.mean_inference_latency_s,
                3,
            ),
            "mean_cycle_duration_s": round(self.mean_cycle_duration_s, 3),
        }


@dataclass(frozen=True, slots=True)
class AggregationUpdate:
    current: AggregatedEmission
    completed: tuple[AggregatedEmission, ...]


@dataclass(slots=True)
class _WindowState:
    camera_id: str
    camera_database_id: str
    period_start: datetime
    period_end: datetime
    last_captured_at: datetime
    sample_count: int = 0
    vehicle_sums: dict[str, float] = field(
        default_factory=lambda: {vehicle_type: 0.0 for vehicle_type in VEHICLE_TYPES}
    )
    frame_acquisition_latency_sum_s: float = 0.0
    queue_wait_sum_s: float = 0.0
    inference_latency_sum_s: float = 0.0
    cycle_duration_sum_s: float = 0.0

    def add(self, observation: EmissionObservation) -> None:
        self.sample_count += 1
        self.last_captured_at = max(self.last_captured_at, observation.captured_at)
        for vehicle_type in VEHICLE_TYPES:
            self.vehicle_sums[vehicle_type] += observation.vehicle_counts[vehicle_type]
        self.frame_acquisition_latency_sum_s += observation.frame_acquisition_latency_s
        self.queue_wait_sum_s += observation.queue_wait_s
        self.inference_latency_sum_s += observation.inference_latency_s
        self.cycle_duration_sum_s += observation.cycle_duration_s

    def aggregate(
        self,
        emission_calculator: Callable[[Mapping[str, int | float]], Mapping[str, Any]],
    ) -> AggregatedEmission:
        mean_counts = {
            vehicle_type: self.vehicle_sums[vehicle_type] / self.sample_count
            for vehicle_type in VEHICLE_TYPES
        }
        calculated = emission_calculator(mean_counts)
        return AggregatedEmission(
            camera_id=self.camera_id,
            camera_database_id=self.camera_database_id,
            period_start=self.period_start,
            period_end=self.period_end,
            last_captured_at=self.last_captured_at,
            sample_count=self.sample_count,
            mean_vehicle_counts=mean_counts,
            emission={field: float(calculated[field]) for field in EMISSION_RATE_FIELDS},
            mean_frame_acquisition_latency_s=(
                self.frame_acquisition_latency_sum_s / self.sample_count
            ),
            mean_queue_wait_s=self.queue_wait_sum_s / self.sample_count,
            mean_inference_latency_s=self.inference_latency_sum_s / self.sample_count,
            mean_cycle_duration_s=self.cycle_duration_sum_s / self.sample_count,
        )


class EmissionWindowAggregator:
    """Aggregate per-camera snapshots into fixed capture-time windows."""

    def __init__(
        self,
        *,
        window_seconds: int,
        emission_calculator: Callable[
            [Mapping[str, int | float]],
            Mapping[str, Any],
        ] = calculate_emission,
    ):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")
        self.window_seconds = window_seconds
        self.emission_calculator = emission_calculator
        self._windows: dict[tuple[str, datetime], _WindowState] = {}
        self._last_finalized_start: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def add(self, observation: EmissionObservation) -> AggregationUpdate:
        window_start = self.window_start(observation.captured_at)
        window_end = window_start + timedelta(seconds=self.window_seconds)

        with self._lock:
            completed = self._flush_camera_expired_locked(
                observation.camera_id,
                observation.captured_at,
            )
            last_finalized = self._last_finalized_start.get(observation.camera_id)
            if last_finalized is not None and window_start <= last_finalized:
                raise LateEmissionObservation(
                    f"camera {observation.camera_id} window {window_start.isoformat()} "
                    "was already finalized"
                )

            key = (observation.camera_id, window_start)
            state = self._windows.get(key)
            if state is None:
                state = _WindowState(
                    camera_id=observation.camera_id,
                    camera_database_id=observation.camera_database_id,
                    period_start=window_start,
                    period_end=window_end,
                    last_captured_at=observation.captured_at,
                )
                self._windows[key] = state
            state.add(observation)
            current = state.aggregate(self.emission_calculator)
            return AggregationUpdate(current=current, completed=tuple(completed))

    def flush_expired(self, watermark: datetime) -> tuple[AggregatedEmission, ...]:
        _require_aware(watermark, "watermark")
        with self._lock:
            return tuple(self._flush_expired_locked(watermark))

    def flush_all(self) -> tuple[AggregatedEmission, ...]:
        with self._lock:
            states = sorted(
                self._windows.values(),
                key=lambda state: (state.period_start, state.camera_id),
            )
            self._windows.clear()
            return tuple(self._finalize_locked(state) for state in states)

    def preview(self, camera_id: str) -> AggregatedEmission | None:
        with self._lock:
            states = [
                state
                for (state_camera_id, _window_start), state in self._windows.items()
                if state_camera_id == camera_id
            ]
            if not states:
                return None
            latest = max(states, key=lambda state: state.period_start)
            return latest.aggregate(self.emission_calculator)

    def window_start(self, captured_at: datetime) -> datetime:
        _require_aware(captured_at, "captured_at")
        epoch_seconds = int(captured_at.timestamp())
        aligned_epoch = epoch_seconds - (epoch_seconds % self.window_seconds)
        return datetime.fromtimestamp(aligned_epoch, tz=timezone.utc)

    def _flush_expired_locked(self, watermark: datetime) -> list[AggregatedEmission]:
        expired_keys = sorted(
            (
                key
                for key, state in self._windows.items()
                if state.period_end <= watermark
            ),
            key=lambda key: (key[1], key[0]),
        )
        completed = []
        for key in expired_keys:
            state = self._windows.pop(key)
            completed.append(self._finalize_locked(state))
        return completed

    def _flush_camera_expired_locked(
        self,
        camera_id: str,
        watermark: datetime,
    ) -> list[AggregatedEmission]:
        expired_keys = sorted(
            (
                key
                for key, state in self._windows.items()
                if key[0] == camera_id and state.period_end <= watermark
            ),
            key=lambda key: key[1],
        )
        completed = []
        for key in expired_keys:
            state = self._windows.pop(key)
            completed.append(self._finalize_locked(state))
        return completed

    def _finalize_locked(self, state: _WindowState) -> AggregatedEmission:
        self._last_finalized_start[state.camera_id] = state.period_start
        return state.aggregate(self.emission_calculator)
