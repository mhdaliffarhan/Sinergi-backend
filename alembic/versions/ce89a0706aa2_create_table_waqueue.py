"""create table WaQueue

Revision ID: ce89a0706aa2
Revises: 9a49ce214c24
Create Date: 2025-12-03 10:37:59.853708

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce89a0706aa2'
down_revision: Union[str, Sequence[str], None] = '9a49ce214c24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- MANUAL CODE START ---
    op.create_table('wa_queue',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('phone_number', sa.String(length=50), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=True),
    sa.Column('error_log', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wa_queue_id'), 'wa_queue', ['id'], unique=False)
    op.create_index(op.f('ix_wa_queue_status'), 'wa_queue', ['status'], unique=False)
    # --- MANUAL CODE END ---


def downgrade() -> None:
    # --- MANUAL CODE START ---
    op.drop_index(op.f('ix_wa_queue_status'), table_name='wa_queue')
    op.drop_index(op.f('ix_wa_queue_id'), table_name='wa_queue')
    op.drop_table('wa_queue')
    # --- MANUAL CODE END ---
