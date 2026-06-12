"""add material column to productos

Revision ID: a1b2c3d4e5f6
Revises: cd2e95dcae18
Create Date: 2026-06-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'cd2e95dcae18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('productos', sa.Column('material', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('productos', 'material')
