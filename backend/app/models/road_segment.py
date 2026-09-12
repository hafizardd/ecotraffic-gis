import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"
    __table_args__ = (Index("ix_road_segments_geometry_gist", "geometry", postgresql_using="gist"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    road_segment_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geometry: Mapped[Geometry] = mapped_column(Geometry("LINESTRING", srid=4326), nullable=False)
    length_km: Mapped[float] = mapped_column(Float, nullable=False)
    bus_stop_accessibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    population: Mapped[float | None] = mapped_column(Float, nullable=True)
    spatial_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
