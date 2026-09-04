"""add segment emission pipeline tables

Revision ID: f4a1c8d9e2b3
Revises: 33ee7e8f1db5
"""

from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa


revision: str = "f4a1c8d9e2b3"
down_revision: Union[str, None] = "33ee7e8f1db5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "road_segments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("road_segment_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geometry", geoalchemy2.types.Geometry(geometry_type="LINESTRING", srid=4326), nullable=False),
        sa.Column("length_km", sa.Float(), nullable=False),
        sa.Column("bus_stop_accessibility", sa.Float(), nullable=True),
        sa.Column("activity_density", sa.Float(), nullable=True),
        sa.Column("population", sa.Float(), nullable=True),
        sa.Column("spatial_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("road_segment_id"),
    )
    op.create_index("ix_road_segments_geometry_gist", "road_segments", ["geometry"], postgresql_using="gist")
    op.create_table(
        "camera_road_segments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("road_segment_id", sa.UUID(), nullable=False),
        sa.Column("lane_or_stream_id", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["road_segment_id"], ["road_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("camera_id", "road_segment_id", "lane_or_stream_id", "valid_from", name="uq_camera_road_segment_stream_period"),
    )
    op.create_index("ix_camera_road_segments_camera_active", "camera_road_segments", ["camera_id", "is_active"])
    op.create_table(
        "segment_traffic_observations",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("road_segment_id", sa.UUID(), nullable=False),
        sa.Column("camera_id", sa.UUID(), nullable=False), sa.Column("camera_identifier", sa.String(100), nullable=False),
        sa.Column("lane_or_stream_id", sa.String(100), nullable=False), sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_duration_seconds", sa.Float(), nullable=False), sa.Column("vehicle_count_semantics", sa.String(40), nullable=False),
        sa.Column("raw_detected_count", sa.JSON(), nullable=False), sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["road_segment_id"], ["road_segments.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_segment_traffic_observations_segment_period", "segment_traffic_observations", ["road_segment_id", "captured_at"])
    op.create_index("ix_segment_traffic_observations_camera_stream_period", "segment_traffic_observations", ["camera_id", "lane_or_stream_id", "captured_at"])
    op.create_table(
        "segment_emissions",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("road_segment_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False), sa.Column("period_end", sa.DateTime(timezone=True), nullable=False), sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculation_version", sa.Integer(), nullable=False), sa.Column("observation_duration_seconds", sa.Float(), nullable=False), sa.Column("aggregation_policy", sa.String(50), nullable=False),
        sa.Column("source_cameras", sa.JSON(), nullable=False), sa.Column("source_streams", sa.JSON(), nullable=False), sa.Column("source_observation_count", sa.Integer(), nullable=False),
        sa.Column("raw_counts", sa.JSON(), nullable=False), sa.Column("volume_per_hour", sa.JSON(), nullable=False), sa.Column("vkt_km_h", sa.JSON(), nullable=False), sa.Column("pollutant_totals_g_h", sa.JSON(), nullable=False), sa.Column("category_pollutant_breakdown_g_h", sa.JSON(), nullable=False),
         sa.Column("raw_criteria", sa.JSON(), nullable=False), sa.Column("normalized_criteria", sa.JSON(), nullable=True), sa.Column("decision_score", sa.Float(), nullable=True), sa.Column("priority", sa.String(20), nullable=True), sa.Column("spatial_criteria_status", sa.String(30), nullable=False), sa.Column("ahp_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["road_segment_id"], ["road_segments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("road_segment_id", "period_start", "calculation_version", name="uq_segment_emission_period_version"),
    )
    op.create_index("ix_segment_emissions_segment_period", "segment_emissions", ["road_segment_id", "period_end"])


def downgrade() -> None:
    op.drop_index("ix_segment_emissions_segment_period", table_name="segment_emissions")
    op.drop_table("segment_emissions")
    op.drop_index("ix_segment_traffic_observations_camera_stream_period", table_name="segment_traffic_observations")
    op.drop_index("ix_segment_traffic_observations_segment_period", table_name="segment_traffic_observations")
    op.drop_table("segment_traffic_observations")
    op.drop_index("ix_camera_road_segments_camera_active", table_name="camera_road_segments")
    op.drop_table("camera_road_segments")
    op.drop_index("ix_road_segments_geometry_gist", table_name="road_segments")
    op.drop_table("road_segments")
