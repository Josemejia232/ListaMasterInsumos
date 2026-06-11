"""change cache_entries value from String(5000) to Text

Revision ID: 799a0f637b5f
Revises: 9f0da88b357d
Create Date: 2026-06-11 10:10:10.326967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '799a0f637b5f'
down_revision: Union[str, None] = '9f0da88b357d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip for SQLite (doesn't support ALTER COLUMN TYPE)
    # PostgreSQL only: change VARCHAR(5000) to TEXT
    try:
        op.alter_column('cache_entries', 'value',
                   existing_type=sa.VARCHAR(length=5000),
                   type_=sa.Text(),
                   existing_nullable=False)
    except Exception:
        pass  # SQLite or already applied


def downgrade() -> None:
    try:
        op.alter_column('cache_entries', 'value',
                   existing_type=sa.Text(),
                   type_=sa.VARCHAR(length=5000),
                   existing_nullable=False)
    except Exception:
        pass
