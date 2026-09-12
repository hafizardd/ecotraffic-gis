"""Add time-first analytics indexes; keep existing segment-first unique index.

Revision ID: a8b3c2d1e9f0
Revises: 9d2c6f1a4b8e
"""
from alembic import op

revision = "a8b3c2d1e9f0"
down_revision = "9d2c6f1a4b8e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_segment_emissions_period_segment", "segment_emissions", ["period_start", "road_segment_id"])
    op.create_index("ix_segment_emissions_calculated_at", "segment_emissions", ["calculated_at"])


def downgrade():
    op.drop_index("ix_segment_emissions_calculated_at", table_name="segment_emissions")
    op.drop_index("ix_segment_emissions_period_segment", table_name="segment_emissions")
