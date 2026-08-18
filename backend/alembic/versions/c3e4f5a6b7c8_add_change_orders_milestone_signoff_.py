"""add change orders, milestone sign-off, and project close-out/clone fields

Revision ID: c3e4f5a6b7c8
Revises: b2d3e4f5a6b7
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'b2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'change_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('amount_delta', sa.Numeric(12, 2), nullable=True),
        sa.Column('hours_delta', sa.Numeric(6, 2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('requested_date', sa.Date(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('decided_by_email', sa.String(length=255), nullable=True),
        sa.Column('decided_by_name', sa.String(length=255), nullable=True),
        sa.Column('created_by_email', sa.String(length=255), nullable=False),
        sa.Column('created_by_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_orders_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_orders_contract_id'), ['contract_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_orders_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_orders_change_type'), ['change_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_orders_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_orders_deleted_at'), ['deleted_at'], unique=False)

    with op.batch_alter_table('milestones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approval_status', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('approved_by_email', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('approved_by_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_milestones_approval_status'), ['approval_status'], unique=False)

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('close_out_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('cloned_from_project_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_projects_cloned_from_project_id'), ['cloned_from_project_id'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_projects_cloned_from_project_id_projects', 'projects', ['cloned_from_project_id'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_constraint('fk_projects_cloned_from_project_id_projects', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_projects_cloned_from_project_id'))
        batch_op.drop_column('cloned_from_project_id')
        batch_op.drop_column('close_out_notes')

    with op.batch_alter_table('milestones', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_milestones_approval_status'))
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('approved_by_name')
        batch_op.drop_column('approved_by_email')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approval_status')

    with op.batch_alter_table('change_orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_change_orders_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_change_orders_status'))
        batch_op.drop_index(batch_op.f('ix_change_orders_change_type'))
        batch_op.drop_index(batch_op.f('ix_change_orders_project_id'))
        batch_op.drop_index(batch_op.f('ix_change_orders_contract_id'))
        batch_op.drop_index(batch_op.f('ix_change_orders_id'))
    op.drop_table('change_orders')
