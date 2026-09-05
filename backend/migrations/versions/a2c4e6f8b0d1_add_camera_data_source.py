"""add camera data source classification"""

from alembic import op
import sqlalchemy as sa

revision = "a2c4e6f8b0d1"
down_revision = "f4a1c8d9e2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cameras", sa.Column("data_source", sa.String(20), nullable=False, server_default="HISTORICAL"))
    op.execute("UPDATE cameras SET data_source = 'LIVE' WHERE stream_url ILIKE '%ATCS_jlagran.stream/playlist.m3u8' OR stream_url ILIKE '%ANPR-Jl-Wardhani.stream/playlist.m3u8'")


def downgrade() -> None:
    op.drop_column("cameras", "data_source")
