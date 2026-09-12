"""mark non-LIVE cameras as precomputed replay sources

The 54 non-LIVE cameras are no longer sampled. Their facts ship as the
precomputed REPLAY dataset, so relabel them ``data_source = 'REPLAY'`` to make
"not live / not being sampled" explicit. ``is_active`` is deliberately left
untouched so the cameras stay visible on the map and in ``GET /api/cameras``.

Revision ID: a3d5f7b9c1e2
Revises: e1f2a3b4c5d6
Create Date: 2026-09-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a3d5f7b9c1e2"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE cameras SET data_source = 'REPLAY' WHERE data_source <> 'LIVE'")


def downgrade() -> None:
    op.execute("UPDATE cameras SET data_source = 'HISTORICAL' WHERE data_source = 'REPLAY'")
