import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SurveyStopObservation(Base):
    __tablename__ = "survey_stop_observations"
    __table_args__ = (Index("ix_survey_stop_observations_geometry_gist", "geometry", postgresql_using="gist"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    geometry: Mapped[Geometry] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    media: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    observer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    facility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pedestrian_access_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    environment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_activity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    survey_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manual_score_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    accessibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    intervention_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    intervention_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class PointOfInterest(Base):
    __tablename__ = "points_of_interest"
    __table_args__ = (
        Index("ix_points_of_interest_geometry_gist", "geometry", postgresql_using="gist"),
        Index("ix_points_of_interest_category", "category"),
        Index("ix_points_of_interest_type_1", "type_1"),
        Index("ix_points_of_interest_type_2", "type_2"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_3: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    geometry: Mapped[Geometry] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class PopulationZone(Base):
    __tablename__ = "population_zones"
    __table_args__ = (
        UniqueConstraint("district_name", name="uq_population_zones_district_name"),
        Index("ix_population_zones_geometry_gist", "geometry", postgresql_using="gist"),
        Index("ix_population_zones_district_name", "district_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    district_name: Mapped[str] = mapped_column(String(255), nullable=False)
    population: Mapped[int] = mapped_column(BigInteger, nullable=False)
    geometry: Mapped[Geometry] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
