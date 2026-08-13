"""add time_entries for time tracking and utilization

Revision ID: f86923b5c203
Revises: 29ba39bf7814
Create Date: 2026-08-13 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f86923b5c203'
down_revision: Union[str, Sequence[str], None] = '29ba39bf7814'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'time_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=False),
        sa.Column('hours', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('billable', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('time_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_time_entries_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_time_entries_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_time_entries_task_id'), ['task_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_time_entries_user_email'), ['user_email'], unique=False)
        batch_op.create_index(batch_op.f('ix_time_entries_entry_date'), ['entry_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_time_entries_billable'), ['billable'], unique=False)
        batch_op.create_index(batch_op.f('ix_time_entries_deleted_at'), ['deleted_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('time_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_time_entries_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_time_entries_billable'))
        batch_op.drop_index(batch_op.f('ix_time_entries_entry_date'))
        batch_op.drop_index(batch_op.f('ix_time_entries_user_email'))
        batch_op.drop_index(batch_op.f('ix_time_entries_task_id'))
        batch_op.drop_index(batch_op.f('ix_time_entries_project_id'))
        batch_op.drop_index(batch_op.f('ix_time_entries_id'))

    op.drop_table('time_entries')
