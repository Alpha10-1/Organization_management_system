"""add projects (engagements) and task-to-project link

Revision ID: 29ba39bf7814
Revises: 383cb2005007
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29ba39bf7814'
down_revision: Union[str, Sequence[str], None] = '383cb2005007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='other'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='planning'),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('budget', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('engagement_partner_email', sa.String(length=255), nullable=True),
        sa.Column('engagement_partner_name', sa.String(length=255), nullable=True),
        sa.Column('engagement_manager_email', sa.String(length=255), nullable=True),
        sa.Column('engagement_manager_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=False, server_default='low'),
        sa.Column('compliance_flag', sa.String(length=50), nullable=True),
        sa.Column('created_by_email', sa.String(length=255), nullable=False),
        sa.Column('created_by_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_projects_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_projects_client_id'), ['client_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_projects_type'), ['type'], unique=False)
        batch_op.create_index(batch_op.f('ix_projects_status'), ['status'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_projects_engagement_partner_email'), ['engagement_partner_email'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_projects_engagement_manager_email'), ['engagement_manager_email'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_projects_risk_level'), ['risk_level'], unique=False)
        batch_op.create_index(batch_op.f('ix_projects_deleted_at'), ['deleted_at'], unique=False)

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_tasks_project_id'), ['project_id'], unique=False)
        batch_op.create_foreign_key('fk_tasks_project_id_projects', 'projects', ['project_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_tasks_project_id_projects', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_tasks_project_id'))
        batch_op.drop_column('project_id')

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_projects_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_projects_risk_level'))
        batch_op.drop_index(batch_op.f('ix_projects_engagement_manager_email'))
        batch_op.drop_index(batch_op.f('ix_projects_engagement_partner_email'))
        batch_op.drop_index(batch_op.f('ix_projects_status'))
        batch_op.drop_index(batch_op.f('ix_projects_type'))
        batch_op.drop_index(batch_op.f('ix_projects_client_id'))
        batch_op.drop_index(batch_op.f('ix_projects_id'))

    op.drop_table('projects')
