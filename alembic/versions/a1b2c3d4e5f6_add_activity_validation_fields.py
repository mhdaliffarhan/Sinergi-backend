"""add activity validation fields

Revision ID: a1b2c3d4e5f6
Revises: e6f7a6b5c4d3
Create Date: 2026-03-13 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e6f7a6b5c4d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to aktivitas table
    op.add_column('aktivitas', sa.Column('validated_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('aktivitas', sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('aktivitas', sa.Column('catatan_validator', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('aktivitas', 'catatan_validator')
    op.drop_column('aktivitas', 'validated_at')
    op.drop_column('aktivitas', 'validated_by_id')
