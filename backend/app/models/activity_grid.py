import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActivityGridHex(Base):
    """One hex cell of the offline AHP activity-potential model.

    Raw AHP outputs (``skor_total_ahp``, ``ranking``, ``klasifikasi_potensi``)
    and the normalized inputs are both stored so the detail panel can explain
    "why" without recomputation, mirroring RoadSegment/SegmentEmission.
    """

    __tablename__ = "activity_grid_hexes"
    __table_args__ = (Index("ix_activity_grid_hexes_geometry_gist", "geometry", postgresql_using="gist"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hex_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    geometry: Mapped[Geometry] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    luas_km2: Mapped[float] = mapped_column(Float, nullable=False)
    poi_total: Mapped[int] = mapped_column(Integer, nullable=False)
    poi_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False)
    penduduk: Mapped[int] = mapped_column(Integer, nullable=False)
    volume_mean: Mapped[float] = mapped_column(Float, nullable=False)
    norm_volume: Mapped[float] = mapped_column(Float, nullable=False)
    norm_poi: Mapped[float] = mapped_column(Float, nullable=False)
    norm_penduduk: Mapped[float] = mapped_column(Float, nullable=False)
    skor_total_ahp: Mapped[float] = mapped_column(Float, nullable=False)
    ranking: Mapped[int] = mapped_column(Integer, nullable=False)
    klasifikasi_potensi: Mapped[str] = mapped_column(String(40), nullable=False)
    ahp_weight_version: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
