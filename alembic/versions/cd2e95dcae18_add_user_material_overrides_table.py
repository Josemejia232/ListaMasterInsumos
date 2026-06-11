"""add user_material_overrides table

Revision ID: cd2e95dcae18
Revises: 799a0f637b5f
Create Date: 2026-06-11 11:14:30.084001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd2e95dcae18'
down_revision: Union[str, None] = '799a0f637b5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_material_overrides',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=200), nullable=False),
    sa.Column('unidad', sa.String(length=50), nullable=False),
    sa.Column('cantidad', sa.Float(), nullable=False),
    sa.Column('vr_unitario', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_material_overrides_usuario_id'), 'user_material_overrides', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_material_overrides_usuario_id'), table_name='user_material_overrides')
    op.drop_table('user_material_overrides')
