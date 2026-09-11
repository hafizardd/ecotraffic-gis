"""add survey AHP scores, facility checklist and damage indicators to bus stops

Revision ID: e1f2a3b4c5d6
Revises: c2d3e4f5a6b7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = (
    ("accessibility_score_100", sa.Float()),
    ("condition_score_100", sa.Float()),
    ("environment_score_100", sa.Float()),
    ("ahp_total_score", sa.Float()),
    ("ahp_rank", sa.Integer()),
    ("ahp_classification", sa.String(40)),
    ("ahp_weight_version", sa.String(40)),
    ("facility_checklist", postgresql.JSONB()),
    ("damage_indicators", postgresql.JSONB()),
    ("poi_breakdown_survey", postgresql.JSONB()),
)


def upgrade() -> None:
    for name, column_type in _COLUMNS:
        op.add_column("survey_stop_observations", sa.Column(name, column_type, nullable=True))
    op.create_index(
        "ix_survey_stop_observations_ahp_classification",
        "survey_stop_observations",
        ["ahp_classification"],
    )


def downgrade() -> None:
    op.drop_index("ix_survey_stop_observations_ahp_classification", table_name="survey_stop_observations")
    for name, _ in reversed(_COLUMNS):
        op.drop_column("survey_stop_observations", name)
