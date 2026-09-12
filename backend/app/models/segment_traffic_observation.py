import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SegmentTrafficObservationRecord(Base):
    __tablename__ = "segment_traffic_observations"
    __table_args__ = (
        Index(
            "ix_segment_traffic_observations_segment_period",
            "road_segment_id", "captured_at",
        ),
        Index(
            "ix_segment_traffic_observations_camera_stream_period",
            "camera_id", "lane_or_stream_id", "captured_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    road_segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="CASCADE"), nullable=False
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    camera_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    lane_or_stream_id: Mapped[str] = mapped_column(String(100), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observation_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    vehicle_count_semantics: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_detected_count: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
