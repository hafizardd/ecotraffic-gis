import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SegmentEmission(Base):
    __tablename__ = "segment_emissions"
    __table_args__ = (
        UniqueConstraint("road_segment_id", "period_start", "calculation_version", name="uq_segment_emission_period_version"),
        Index("ix_segment_emissions_segment_period", "road_segment_id", "period_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    road_segment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="CASCADE"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculation_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    observation_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    aggregation_policy: Mapped[str] = mapped_column(String(50), nullable=False)
    source_cameras: Mapped[list] = mapped_column(JSONB, nullable=False)
    source_streams: Mapped[list] = mapped_column(JSONB, nullable=False)
    source_observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_counts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    volume_per_hour: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    vkt_km_h: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pollutant_totals_g_h: Mapped[dict] = mapped_column(JSONB, nullable=False)
    category_pollutant_breakdown_g_h: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_criteria: Mapped[dict] = mapped_column(JSONB, nullable=True)
    decision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    spatial_criteria_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    ahp_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False)
