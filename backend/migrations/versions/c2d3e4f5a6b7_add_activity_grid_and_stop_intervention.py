"""add activity grid hexes and bus stop intervention columns

Revision ID: c2d3e4f5a6b7
Revises: a8b3c2d1e9f0
"""

from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "a8b3c2d1e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_grid_hexes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hex_id", sa.Integer(), nullable=False),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("luas_km2", sa.Float(), nullable=False),
        sa.Column("poi_total", sa.Integer(), nullable=False),
        sa.Column("poi_breakdown", postgresql.JSONB(), nullable=False),
        sa.Column("penduduk", sa.Integer(), nullable=False),
        sa.Column("volume_mean", sa.Float(), nullable=False),
        sa.Column("norm_volume", sa.Float(), nullable=False),
        sa.Column("norm_poi", sa.Float(), nullable=False),
        sa.Column("norm_penduduk", sa.Float(), nullable=False),
        sa.Column("skor_total_ahp", sa.Float(), nullable=False),
        sa.Column("ranking", sa.Integer(), nullable=False),
        sa.Column("klasifikasi_potensi", sa.String(40), nullable=False),
        sa.Column("ahp_weight_version", sa.String(40), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hex_id"),
    )
    op.create_index("ix_activity_grid_hexes_geometry_gist", "activity_grid_hexes", ["geometry"], postgresql_using="gist")
    for column in ("accessibility_score", "intervention_score"):
        op.add_column("survey_stop_observations", sa.Column(column, sa.Float(), nullable=True))
    op.add_column("survey_stop_observations", sa.Column("intervention_rank", sa.Integer(), nullable=True))
    op.add_column("survey_stop_observations", sa.Column("intervention_class", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("survey_stop_observations", "intervention_class")
    op.drop_column("survey_stop_observations", "intervention_rank")
    op.drop_column("survey_stop_observations", "intervention_score")
    op.drop_column("survey_stop_observations", "accessibility_score")
    op.drop_index("ix_activity_grid_hexes_geometry_gist", table_name="activity_grid_hexes")
    op.drop_table("activity_grid_hexes")
