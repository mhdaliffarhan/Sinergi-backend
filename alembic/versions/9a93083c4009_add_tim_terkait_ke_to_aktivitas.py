"""Add tim terkait ke to aktivitas

Revision ID: 9a93083c4009
Revises: 5c434a1f5bbd
Create Date: 2025-11-24 12:40:30.346228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a93083c4009'
down_revision: Union[str, Sequence[str], None] = '5c434a1f5bbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
   op.create_table(
        'aktivitas_tim_terkait_link',
        sa.Column('aktivitas_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['aktivitas_id'], ['aktivitas.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('aktivitas_id', 'team_id')
    )


def downgrade() -> None:
    op.drop_table('aktivitas_tim_terkait_link')
