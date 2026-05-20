import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Emission(Base):
    __tablename__ = "emissions"
    __table_args__ = (
        # Composite index — speeds up "last N rows for camera X" queries
        # and "most recent row per camera" queries
        Index("ix_emissions_camera_id_timestamp", "camera_id", "timestamp"),
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
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time when the detection cycle ran — set explicitly by worker",
    )

    # --- Vehicle counts ---
    car: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    motorcycle: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    truck: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Calculated CO emission ---
    total_co_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_co_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)

    # NOx
    total_nox_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_nox_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)

    # PM
    total_pm_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_pm_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)

    # NMVOC
    total_nmvoc_g_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    total_nmvoc_kg_per_hr: Mapped[float] = mapped_column(Float, nullable=False)

    # --- Performance tracking ---
    cycle_duration_s: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="How long the detection cycle took in seconds",
    )

    # Relationship — back to parent camera
    camera: Mapped["Camera"] = relationship(  # noqa: F821
        "Camera",
        back_populates="emissions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Emission camera={self.camera_id} "
            f"ts={self.timestamp} "
            f"co2={self.total_g_per_min}g/min>"
            f"nox={self.total_nox_g_per_min}g/min>"
            f"pm={self.total_pm_g_per_min}g/min>"
            f"nmvoc={self.total_nmvoc_g_per_min}g/min>"
        )