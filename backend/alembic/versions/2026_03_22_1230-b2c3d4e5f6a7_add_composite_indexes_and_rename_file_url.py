"""add_composite_indexes_and_rename_file_url

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-22 12:30:00.000000

Changes:
1. Rename outputs.file_url → outputs.file_path (technical debt fix)
2. Add composite index (user_id, created_at) on videos table
3. Add composite index (video_id, created_at) on outputs table
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename column: file_url → file_path
    op.alter_column(
        'outputs', 'file_url',
        new_column_name='file_path',
    )

    # 2. Add composite indexes for pagination performance
    op.create_index(
        'ix_videos_user_created', 'videos',
        ['user_id', 'created_at'],
    )
    op.create_index(
        'ix_outputs_video_created', 'outputs',
        ['video_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_outputs_video_created', table_name='outputs')
    op.drop_index('ix_videos_user_created', table_name='videos')
    op.alter_column(
        'outputs', 'file_path',
        new_column_name='file_url',
    )
