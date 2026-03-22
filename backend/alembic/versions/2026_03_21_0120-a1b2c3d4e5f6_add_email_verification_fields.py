"""add_email_verification_fields

Revision ID: a1b2c3d4e5f6
Revises: 5d21994f05aa
Create Date: 2026-03-21 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5d21994f05aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'users',
        sa.Column('email_verified_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'is_email_verified')
