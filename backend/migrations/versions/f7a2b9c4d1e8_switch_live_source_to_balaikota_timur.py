"""switch live CCTV source from wardhani to balaikota timur

Revision ID: f7a2b9c4d1e8
Revises: d3e7b2c1a8f6
Create Date: 2026-09-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f7a2b9c4d1e8"
down_revision: Union[str, Sequence[str], None] = "d3e7b2c1a8f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE cameras SET data_source = 'HISTORICAL'
        WHERE camera_id = 'kotabaru_wardhani'
    """)
    op.execute("""
        UPDATE cameras SET data_source = 'LIVE'
        WHERE camera_id = 'atcs_balaikota_timur'
    """)

    op.execute("""
        UPDATE camera_road_segments existing
        SET is_active = false, valid_to = COALESCE(valid_to, now())
        FROM cameras c
        WHERE c.id = existing.camera_id
          AND c.camera_id = 'kotabaru_wardhani'
          AND existing.is_active = true
    """)

    op.execute("""
        UPDATE camera_road_segments existing
        SET is_active = false, valid_to = COALESCE(valid_to, now())
        FROM cameras c
        WHERE c.id = existing.camera_id
          AND c.camera_id = 'atcs_balaikota_timur'
          AND existing.road_segment_id <> (
              SELECT id FROM road_segments WHERE road_segment_id = 'SEG-0137'
          )
          AND existing.is_active = true
    """)

    op.execute("""
        UPDATE camera_road_segments existing
        SET is_active = false, valid_to = COALESCE(valid_to, now())
        WHERE existing.road_segment_id = (
            SELECT id FROM road_segments WHERE road_segment_id = 'SEG-0137'
        )
          AND existing.camera_id <> (
              SELECT id FROM cameras WHERE camera_id = 'atcs_balaikota_timur'
          )
          AND existing.is_active = true
    """)

    op.execute("""
        INSERT INTO camera_road_segments (id, camera_id, road_segment_id, lane_or_stream_id, is_active)
        SELECT gen_random_uuid(), c.id, s.id, 'default', true
        FROM cameras c CROSS JOIN road_segments s
        WHERE c.camera_id = 'atcs_balaikota_timur'
          AND s.road_segment_id = 'SEG-0137'
          AND NOT EXISTS (
              SELECT 1 FROM camera_road_segments existing
              WHERE existing.camera_id = c.id AND existing.road_segment_id = s.id
                AND existing.lane_or_stream_id = 'default' AND existing.valid_from IS NULL
          )
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE cameras SET data_source = 'LIVE'
        WHERE camera_id = 'kotabaru_wardhani'
    """)
    op.execute("""
        UPDATE cameras SET data_source = 'HISTORICAL'
        WHERE camera_id = 'atcs_balaikota_timur'
    """)