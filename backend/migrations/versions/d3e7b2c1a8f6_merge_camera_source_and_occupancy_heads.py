"""Merge camera source and occupancy segment migration heads.

Revision ID: d3e7b2c1a8f6
Revises: a2c4e6f8b0d1, e6f2a1b3c4d5
"""

from typing import Sequence, Union


revision: str = "d3e7b2c1a8f6"
down_revision: Union[str, Sequence[str], None] = (
    "a2c4e6f8b0d1",
    "e6f2a1b3c4d5",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
