"""merge camera health and emission pillars

Revision ID: 33ee7e8f1db5
Revises: c11a4e9f7b2d, c7d4e9a1f2b3
Create Date: 2026-09-03 04:56:58.871500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33ee7e8f1db5'
down_revision: Union[str, None] = ('c11a4e9f7b2d', 'c7d4e9a1f2b3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
