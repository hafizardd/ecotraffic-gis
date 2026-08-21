"""Idempotent persistence for completed emission aggregation windows."""

from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.core.database import get_sync_db
from app.models.emission_aggregate import EmissionAggregate
from app.services.emission_aggregation import AggregatedEmission


class HistoricalEmissionStore:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Any]] = get_sync_db,
    ) -> None:
        self.session_factory = session_factory

    def save_many(self, aggregates: Iterable[AggregatedEmission]) -> int:
        rows = [self.row_for(aggregate) for aggregate in aggregates]
        if not rows:
            return 0

        statement = insert(EmissionAggregate).values(rows)
        update_values = {
            column: getattr(statement.excluded, column)
            for column in rows[0]
            if column not in {"id", "camera_id", "period_start"}
        }
        statement = statement.on_conflict_do_update(
            constraint="uq_emission_aggregates_camera_period_start",
            set_=update_values,
        )
        with self.session_factory() as db:
            db.execute(statement)
        return len(rows)

    @staticmethod
    def row_for(aggregate: AggregatedEmission) -> dict[str, Any]:
        return {
            "id": uuid.uuid4(),
            "camera_id": uuid.UUID(aggregate.camera_database_id),
            "period_start": aggregate.period_start,
            "period_end": aggregate.period_end,
            "last_captured_at": aggregate.last_captured_at,
            "sample_count": aggregate.sample_count,
            "aggregation_method": "arithmetic_mean_of_snapshot_counts",
            "vehicle_count_semantics": "mean_observed_snapshot_count",
            "car": aggregate.mean_vehicle_counts["car"],
            "motorcycle": aggregate.mean_vehicle_counts["motorcycle"],
            "bus": aggregate.mean_vehicle_counts["bus"],
            "truck": aggregate.mean_vehicle_counts["truck"],
            **dict(aggregate.emission),
            "mean_frame_acquisition_latency_s": (
                aggregate.mean_frame_acquisition_latency_s
            ),
            "mean_queue_wait_s": aggregate.mean_queue_wait_s,
            "mean_inference_latency_s": aggregate.mean_inference_latency_s,
            "cycle_duration_s": aggregate.mean_cycle_duration_s,
        }
