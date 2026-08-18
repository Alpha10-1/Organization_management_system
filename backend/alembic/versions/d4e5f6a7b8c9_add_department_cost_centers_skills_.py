"""add department cost centers, task template checklist triggers, skills matrix, resource requests, and leave requests

Revision ID: d4e5f6a7b8c9
Revises: c3e4f5a6b7c8
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('annual_budget', sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column('cost_center_code', sa.String(length=50), nullable=True))
        batch_op.create_index(batch_op.f('ix_departments_cost_center_code'), ['cost_center_code'], unique=False)

    with op.batch_alter_table('task_templates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trigger_event', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('department_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_task_templates_trigger_event'), ['trigger_event'], unique=False)
        batch_op.create_index(batch_op.f('ix_task_templates_department_id'), ['department_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_task_templates_department_id_departments', 'departments', ['department_id'], ['id']
        )

    op.create_table(
        'staff_skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('proficiency_level', sa.String(length=20), nullable=True),
        sa.Column('issued_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_email', sa.String(length=255), nullable=False),
        sa.Column('created_by_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('staff_skills', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_staff_skills_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_staff_skills_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_staff_skills_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_staff_skills_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_staff_skills_expiry_date'), ['expiry_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_staff_skills_deleted_at'), ['deleted_at'], unique=False)

    op.create_table(
        'resource_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requesting_department_id', sa.Integer(), nullable=False),
        sa.Column('providing_department_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('requested_user_id', sa.Integer(), nullable=True),
        sa.Column('role_needed', sa.String(length=100), nullable=True),
        sa.Column('allocation_percent', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('decided_by_email', sa.String(length=255), nullable=True),
        sa.Column('decided_by_name', sa.String(length=255), nullable=True),
        sa.Column('requested_by_email', sa.String(length=255), nullable=False),
        sa.Column('requested_by_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requesting_department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['providing_department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['requested_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('resource_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_resource_requests_id'), ['id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_resource_requests_requesting_department_id'), ['requesting_department_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_resource_requests_providing_department_id'), ['providing_department_id'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_resource_requests_project_id'), ['project_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_resource_requests_requested_user_id'), ['requested_user_id'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_resource_requests_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_resource_requests_deleted_at'), ['deleted_at'], unique=False)

    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('approver_user_id', sa.Integer(), nullable=False),
        sa.Column('leave_type', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('decided_by_email', sa.String(length=255), nullable=True),
        sa.Column('decided_by_name', sa.String(length=255), nullable=True),
        sa.Column('decision_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approver_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('leave_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_leave_requests_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_leave_requests_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_leave_requests_approver_user_id'), ['approver_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_leave_requests_leave_type'), ['leave_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_leave_requests_start_date'), ['start_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_leave_requests_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_leave_requests_deleted_at'), ['deleted_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('leave_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_leave_requests_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_leave_requests_status'))
        batch_op.drop_index(batch_op.f('ix_leave_requests_start_date'))
        batch_op.drop_index(batch_op.f('ix_leave_requests_leave_type'))
        batch_op.drop_index(batch_op.f('ix_leave_requests_approver_user_id'))
        batch_op.drop_index(batch_op.f('ix_leave_requests_user_id'))
        batch_op.drop_index(batch_op.f('ix_leave_requests_id'))
    op.drop_table('leave_requests')

    with op.batch_alter_table('resource_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_resource_requests_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_resource_requests_status'))
        batch_op.drop_index(batch_op.f('ix_resource_requests_requested_user_id'))
        batch_op.drop_index(batch_op.f('ix_resource_requests_project_id'))
        batch_op.drop_index(batch_op.f('ix_resource_requests_providing_department_id'))
        batch_op.drop_index(batch_op.f('ix_resource_requests_requesting_department_id'))
        batch_op.drop_index(batch_op.f('ix_resource_requests_id'))
    op.drop_table('resource_requests')

    with op.batch_alter_table('staff_skills', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_staff_skills_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_staff_skills_expiry_date'))
        batch_op.drop_index(batch_op.f('ix_staff_skills_category'))
        batch_op.drop_index(batch_op.f('ix_staff_skills_name'))
        batch_op.drop_index(batch_op.f('ix_staff_skills_user_id'))
        batch_op.drop_index(batch_op.f('ix_staff_skills_id'))
    op.drop_table('staff_skills')

    with op.batch_alter_table('task_templates', schema=None) as batch_op:
        batch_op.drop_constraint('fk_task_templates_department_id_departments', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_task_templates_department_id'))
        batch_op.drop_index(batch_op.f('ix_task_templates_trigger_event'))
        batch_op.drop_column('department_id')
        batch_op.drop_column('trigger_event')

    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_departments_cost_center_code'))
        batch_op.drop_column('cost_center_code')
        batch_op.drop_column('annual_budget')
