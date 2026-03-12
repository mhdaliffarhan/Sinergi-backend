"""add wa reminders and update wa_queue

Revision ID: e6f7a6b5c4d3
Revises: d5c7246b835c
Create Date: 2026-03-13 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a6b5c4d3'
down_revision: Union[str, Sequence[str], None] = 'd5c7246b835c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create aktivitas_reminders table
    op.create_table('aktivitas_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aktivitas_id', sa.Integer(), sa.ForeignKey('aktivitas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reminder_type', sa.String(length=20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aktivitas_reminders_id'), 'aktivitas_reminders', ['id'], unique=False)
    op.create_index(op.f('ix_aktivitas_reminders_status'), 'aktivitas_reminders', ['status'], unique=False)

    # 2. Update wa_queue table
    op.add_column('wa_queue', sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('wa_queue', sa.Column('aktivitas_id', sa.Integer(), sa.ForeignKey('aktivitas.id', ondelete='CASCADE'), nullable=True))
    
    # Update status comment/length if necessary (optional)
    # sa.Column('status', sa.String(length=20), default="pending", index=True) # 'pending', 'sent', 'failed', 'cancelled'


def downgrade() -> None:
    op.drop_column('wa_queue', 'aktivitas_id')
    op.drop_column('wa_queue', 'scheduled_at')
    op.drop_index(op.f('ix_aktivitas_reminders_status'), table_name='aktivitas_reminders')
    op.drop_index(op.f('ix_aktivitas_reminders_id'), table_name='aktivitas_reminders')
    op.drop_table('aktivitas_reminders')
