"""replace legacy pollutant columns with the eight dashboard emissions

Revision ID: c7d4e9a1f2b3
Revises: b9e10c4d2a7f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d4e9a1f2b3"
down_revision: Union[str, None] = "b9e10c4d2a7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMISSIONS = ("tsp", "so2", "hc", "co2", "ch4", "n2o")


def _add_new_columns(table_name: str) -> None:
    for pollutant in EMISSIONS:
        op.add_column(table_name, sa.Column(f"total_{pollutant}_g_per_min", sa.Float(), nullable=True))
        op.add_column(table_name, sa.Column(f"total_{pollutant}_kg_per_hr", sa.Float(), nullable=True))


def _make_columns_required(table_name: str) -> None:
    for pollutant in EMISSIONS:
        op.alter_column(table_name, f"total_{pollutant}_g_per_min", nullable=False)
        op.alter_column(table_name, f"total_{pollutant}_kg_per_hr", nullable=False)


def _drop_legacy_columns(table_name: str) -> None:
    for pollutant in ("pm", "nmvoc"):
        op.drop_column(table_name, f"total_{pollutant}_g_per_min")
        op.drop_column(table_name, f"total_{pollutant}_kg_per_hr")


def upgrade() -> None:
    _add_new_columns("emissions")
    op.execute(
        """
        UPDATE emissions
        SET total_tsp_g_per_min = COALESCE(total_pm_g_per_min, 0),
            total_tsp_kg_per_hr = COALESCE(total_pm_kg_per_hr, 0),
            total_hc_g_per_min = COALESCE(total_nmvoc_g_per_min, 0),
            total_hc_kg_per_hr = COALESCE(total_nmvoc_kg_per_hr, 0),
            total_so2_g_per_min = 0,
            total_so2_kg_per_hr = 0,
            total_co2_g_per_min = 0,
            total_co2_kg_per_hr = 0,
            total_ch4_g_per_min = 0,
            total_ch4_kg_per_hr = 0,
            total_n2o_g_per_min = 0,
            total_n2o_kg_per_hr = 0
        """
    )
    _make_columns_required("emissions")
    _drop_legacy_columns("emissions")

    _add_new_columns("emission_aggregates")
    op.execute(
        """
        UPDATE emission_aggregates
        SET total_tsp_g_per_min = COALESCE(total_pm_g_per_min, 0),
            total_tsp_kg_per_hr = COALESCE(total_pm_kg_per_hr, 0),
            total_hc_g_per_min = COALESCE(total_nmvoc_g_per_min, 0),
            total_hc_kg_per_hr = COALESCE(total_nmvoc_kg_per_hr, 0),
            total_so2_g_per_min = 0,
            total_so2_kg_per_hr = 0,
            total_co2_g_per_min = 0,
            total_co2_kg_per_hr = 0,
            total_ch4_g_per_min = 0,
            total_ch4_kg_per_hr = 0,
            total_n2o_g_per_min = 0,
            total_n2o_kg_per_hr = 0
        """
    )
    _make_columns_required("emission_aggregates")
    _drop_legacy_columns("emission_aggregates")


def downgrade() -> None:
    # Downgrade preserves the eight-series values where possible. New-only
    # pollutants cannot be represented by the legacy four-series schema.
    for table_name in ("emissions", "emission_aggregates"):
        op.add_column(table_name, sa.Column("total_pm_g_per_min", sa.Float(), nullable=True))
        op.add_column(table_name, sa.Column("total_pm_kg_per_hr", sa.Float(), nullable=True))
        op.add_column(table_name, sa.Column("total_nmvoc_g_per_min", sa.Float(), nullable=True))
        op.add_column(table_name, sa.Column("total_nmvoc_kg_per_hr", sa.Float(), nullable=True))
        op.execute(
            f"""
            UPDATE {table_name}
            SET total_pm_g_per_min = total_tsp_g_per_min,
                total_pm_kg_per_hr = total_tsp_kg_per_hr,
                total_nmvoc_g_per_min = total_hc_g_per_min,
                total_nmvoc_kg_per_hr = total_hc_kg_per_hr
            """
        )
        _make_columns_required(table_name)
        for pollutant in EMISSIONS:
            op.drop_column(table_name, f"total_{pollutant}_g_per_min")
            op.drop_column(table_name, f"total_{pollutant}_kg_per_hr")
