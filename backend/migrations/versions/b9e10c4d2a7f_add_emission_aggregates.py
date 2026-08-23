"""add historical emission aggregates

Revision ID: b9e10c4d2a7f
Revises: 8f0c3a9d71b2
Create Date: 2026-08-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9e10c4d2a7f"
down_revision: Union[str, None] = "8f0c3a9d71b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "emission_aggregates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("aggregation_method", sa.String(length=100), nullable=False),
        sa.Column("vehicle_count_semantics", sa.String(length=100), nullable=False),
        sa.Column("car", sa.Float(), nullable=False),
        sa.Column("motorcycle", sa.Float(), nullable=False),
        sa.Column("bus", sa.Float(), nullable=False),
        sa.Column("truck", sa.Float(), nullable=False),
        sa.Column("total_co_g_per_min", sa.Float(), nullable=False),
        sa.Column("total_co_kg_per_hr", sa.Float(), nullable=False),
        sa.Column("total_nox_g_per_min", sa.Float(), nullable=False),
        sa.Column("total_nox_kg_per_hr", sa.Float(), nullable=False),
        sa.Column("total_pm_g_per_min", sa.Float(), nullable=False),
        sa.Column("total_pm_kg_per_hr", sa.Float(), nullable=False),
        sa.Column("total_nmvoc_g_per_min", sa.Float(), nullable=False),
        sa.Column("total_nmvoc_kg_per_hr", sa.Float(), nullable=False),
        sa.Column("mean_frame_acquisition_latency_s", sa.Float(), nullable=False),
        sa.Column("mean_queue_wait_s", sa.Float(), nullable=False),
        sa.Column("mean_inference_latency_s", sa.Float(), nullable=False),
        sa.Column("cycle_duration_s", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "camera_id",
            "period_start",
            name="uq_emission_aggregates_camera_period_start",
        ),
    )
    op.create_index(
        "ix_emission_aggregates_camera_period_end",
        "emission_aggregates",
        ["camera_id", "period_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_emission_aggregates_camera_period_end",
        table_name="emission_aggregates",
    )
    op.drop_table("emission_aggregates")
