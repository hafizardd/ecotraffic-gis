import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmissionAggregate(Base):
    """One semantically averaged emission snapshot per camera time window."""

    __tablename__ = "emission_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "camera_id",
            "period_start",
            name="uq_emission_aggregates_camera_period_start",
        ),
        Index("ix_emission_aggregates_camera_period_end", "camera_id", "period_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregation_method: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_count_semantics: Mapped[str] = mapped_column(String(100), nullable=False)

    car: Mapped[float] = mapped_column(Float, nullable=False)
    motorcycle: Mapped[float] = mapped_column(Float, nullable=False)
    bus: Mapped[float] = mapped_column(Float, nullable=False)
    truck: Mapped[float] = mapped_column(Float, nullable=False)

    total_co_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_co_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)
    total_nox_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_nox_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)
    total_pm_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_pm_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)
    total_nmvoc_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_nmvoc_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)

    mean_frame_acquisition_latency_s: Mapped[float] = mapped_column(Float, nullable=False)
    mean_queue_wait_s: Mapped[float] = mapped_column(Float, nullable=False)
    mean_inference_latency_s: Mapped[float] = mapped_column(Float, nullable=False)
    cycle_duration_s: Mapped[float] = mapped_column(Float, nullable=False)

    @property
    def timestamp(self) -> datetime:
        """Compatibility timestamp for the existing emission-history schema."""
        return self.last_captured_at
