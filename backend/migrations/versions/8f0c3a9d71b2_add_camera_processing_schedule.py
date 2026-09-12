"""add camera processing schedule

Revision ID: 8f0c3a9d71b2
Revises: 402026177317
Create Date: 2026-08-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f0c3a9d71b2"
down_revision: Union[str, None] = "402026177317"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cameras",
        sa.Column(
            "priority",
            sa.String(length=10),
            nullable=False,
            server_default="medium",
            comment="Processing tier: high, medium, or low",
        ),
    )
    op.add_column(
        "cameras",
        sa.Column(
            "sampling_interval_seconds",
            sa.Integer(),
            nullable=True,
            comment="Optional per-camera sampling interval; null uses the priority default",
        ),
    )
    op.add_column(
        "cameras",
        sa.Column(
            "next_sample_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Next time the scheduler may enqueue camera processing",
        ),
    )
    op.create_index("ix_cameras_next_sample_at", "cameras", ["next_sample_at"])


def downgrade() -> None:
    op.drop_index("ix_cameras_next_sample_at", table_name="cameras")
    op.drop_column("cameras", "next_sample_at")
    op.drop_column("cameras", "sampling_interval_seconds")
    op.drop_column("cameras", "priority")
