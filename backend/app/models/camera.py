import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
 
from app.core.database import Base

class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        UniqueConstraint("camera_id", name="uq_cameras_camera_id"),
    )

    id:Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name:Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name for the camera",
    )

    camera_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Unique slug used in URLs and code, e.g. atcs_urip_sumoharjo",
    )
    stream_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full HLS .m3u8 stream URL",
    )
    referer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="HTTP Referer header required by the CCTV portal",
    )
    location: Mapped[Geometry] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
        comment="PostGIS point — POINT(longitude latitude) in WGS84",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Set False to disable without deleting emission history",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
 
    # Relationship — one camera has many emission rows
    emissions: Mapped[list["Emission"]] = relationship(  # noqa: F821
        "Emission",
        back_populates="camera",
        cascade="all, delete-orphan",
        lazy="noload",   # never auto-load emissions when querying cameras
    )
 
    def __repr__(self) -> str:
        return f"<Camera {self.camera_id}>"