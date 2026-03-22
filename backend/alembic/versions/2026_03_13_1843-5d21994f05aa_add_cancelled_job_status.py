"""add_cancelled_job_status

Revision ID: 5d21994f05aa
Revises: 52570808ac79
Create Date: 2026-03-13 18:43:14.317766

FIX: Add 'cancelled' value to the PostgreSQL job_status ENUM type.
The initial migration only created: queued, processing, completed, failed.
Without this migration, any attempt to set a job's status to 'cancelled'
will crash with a PostgreSQL DataError.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5d21994f05aa'
down_revision: Union[str, None] = '52570808ac79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'cancelled' to the PostgreSQL ENUM type 'job_status'
    # This is PostgreSQL-specific: ALTER TYPE ... ADD VALUE is not transactional,
    # so we must run it outside of a transaction block.
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an ENUM type directly.
    # To fully reverse this, you'd need to:
    # 1. Create a new ENUM without 'cancelled'
    # 2. Alter column to use new ENUM
    # 3. Drop old ENUM
    # This is intentionally left as a no-op for safety.
    pass
