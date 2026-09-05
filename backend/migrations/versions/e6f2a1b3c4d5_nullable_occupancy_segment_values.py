"""Allow occupancy-derived segment results without flow values."""

from alembic import op
import sqlalchemy as sa

revision = "e6f2a1b3c4d5"
down_revision = "f4a1c8d9e2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("segment_emissions", "volume_per_hour", nullable=True)
    op.alter_column("segment_emissions", "vkt_km_h", nullable=True)
    op.add_column("segment_emissions", sa.Column("vehicle_count_semantics", sa.String(40), nullable=False, server_default="unknown"))


def downgrade() -> None:
    op.drop_column("segment_emissions", "vehicle_count_semantics")
    op.alter_column("segment_emissions", "volume_per_hour", nullable=False)
    op.alter_column("segment_emissions", "vkt_km_h", nullable=False)
