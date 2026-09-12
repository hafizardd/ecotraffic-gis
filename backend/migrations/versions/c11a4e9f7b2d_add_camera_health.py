"""add camera health tracking

Revision ID: c11a4e9f7b2d
Revises: b9e10c4d2a7f
Create Date: 2026-08-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c11a4e9f7b2d"
down_revision: Union[str, None] = "b9e10c4d2a7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cameras", sa.Column("last_sample_at", sa.DateTime(timezone=True)))
    op.add_column("cameras", sa.Column("last_success_at", sa.DateTime(timezone=True)))
    op.add_column("cameras", sa.Column("last_error_at", sa.DateTime(timezone=True)))
    op.add_column(
        "cameras",
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "cameras",
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
    )
    op.create_index("ix_cameras_status", "cameras", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cameras_status", table_name="cameras")
    op.drop_column("cameras", "status")
    op.drop_column("cameras", "failure_count")
    op.drop_column("cameras", "last_error_at")
    op.drop_column("cameras", "last_success_at")
    op.drop_column("cameras", "last_sample_at")
