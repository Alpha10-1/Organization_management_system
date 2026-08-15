"""add client business detail and project assignments

Revision ID: f9ab0648f636
Revises: dd16b268bb45
Create Date: 2026-08-15 20:27:52.375364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9ab0648f636'
down_revision: Union[str, Sequence[str], None] = 'dd16b268bb45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('client_type', sa.String(length=20), nullable=False, server_default='business'))
        batch_op.add_column(sa.Column('company_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('registration_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('tax_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('industry', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('website', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('billing_address', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('postal_code', sa.String(length=20), nullable=True))
        batch_op.alter_column('first_name', existing_type=sa.String(length=100), nullable=True)
        batch_op.alter_column('last_name', existing_type=sa.String(length=100), nullable=True)
        batch_op.create_index(batch_op.f('ix_clients_client_type'), ['client_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_clients_company_name'), ['company_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_clients_industry'), ['industry'], unique=False)

    # Existing rows predate client_type; backfill them as "individual" since
    # the original schema required first_name/last_name for every client.
    op.execute("UPDATE clients SET client_type = 'individual' WHERE client_type = 'business'")

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('objectives', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('deliverables', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('stakeholders', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('billing_notes', sa.Text(), nullable=True))

    op.create_table(
        'project_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('assigned_by_email', sa.String(length=255), nullable=False),
        sa.Column('assigned_by_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('project_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_assignments_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_project_assignments_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_project_assignments_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_project_assignments_department_id'), ['department_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('project_assignments')

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('billing_notes')
        batch_op.drop_column('stakeholders')
        batch_op.drop_column('deliverables')
        batch_op.drop_column('objectives')

    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('last_name', existing_type=sa.String(length=100), nullable=False)
        batch_op.alter_column('first_name', existing_type=sa.String(length=100), nullable=False)
        batch_op.drop_index(batch_op.f('ix_clients_industry'))
        batch_op.drop_index(batch_op.f('ix_clients_company_name'))
        batch_op.drop_index(batch_op.f('ix_clients_client_type'))
        batch_op.drop_column('postal_code')
        batch_op.drop_column('country')
        batch_op.drop_column('city')
        batch_op.drop_column('billing_address')
        batch_op.drop_column('website')
        batch_op.drop_column('industry')
        batch_op.drop_column('tax_number')
        batch_op.drop_column('registration_number')
        batch_op.drop_column('company_name')
        batch_op.drop_column('client_type')
