"""add survey, poi, and population source layers

Revision ID: 9d2c6f1a4b8e
Revises: f7a2b9c4d1e8
"""

from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa

revision: str = "9d2c6f1a4b8e"
down_revision: Union[str, None] = "f7a2b9c4d1e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "survey_stop_observations",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("media", sa.JSON(), nullable=False), sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("observer_name", sa.String(255)), sa.Column("facility_score", sa.Float()),
        sa.Column("pedestrian_access_score", sa.Float()), sa.Column("environment_score", sa.Float()),
        sa.Column("user_activity_score", sa.Float()), sa.Column("survey_score", sa.Float()),
        sa.Column("manual_score_override", sa.Float()), sa.Column("score_method", sa.String(80)),
        sa.Column("source_metadata", sa.JSON(), nullable=False), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_survey_stop_observations_geometry_gist", "survey_stop_observations", ["geometry"], postgresql_using="gist")
    op.create_table(
        "points_of_interest",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("source_key", sa.String(500), nullable=False),
        sa.Column("name", sa.String(500)), sa.Column("category", sa.String(255)), sa.Column("type_1", sa.String(255)),
        sa.Column("type_2", sa.String(255)), sa.Column("type_3", sa.String(255)), sa.Column("address", sa.String(1000)),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("source", sa.String(255), nullable=False), sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("source_key"),
    )
    for name, column in (("geometry_gist", "geometry"), ("category", "category"), ("type_1", "type_1"), ("type_2", "type_2")):
        op.create_index(f"ix_points_of_interest_{name}", "points_of_interest", [column], postgresql_using="gist" if name == "geometry_gist" else None)
    op.create_table(
        "population_zones",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("source_key", sa.String(255), nullable=False),
        sa.Column("district_name", sa.String(255), nullable=False), sa.Column("population", sa.BigInteger(), nullable=False),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("source", sa.String(255), nullable=False), sa.Column("reference_year", sa.Integer()),
        sa.Column("source_metadata", sa.JSON(), nullable=False), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"), sa.UniqueConstraint("district_name", name="uq_population_zones_district_name"),
    )
    op.create_index("ix_population_zones_geometry_gist", "population_zones", ["geometry"], postgresql_using="gist")
    op.create_index("ix_population_zones_district_name", "population_zones", ["district_name"])


def downgrade() -> None:
    op.drop_table("population_zones")
    op.drop_table("points_of_interest")
    op.drop_table("survey_stop_observations")
