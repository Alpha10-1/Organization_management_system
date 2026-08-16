"""add staff positions, manager hierarchy, and department heads

Revision ID: a1c2d3e4f5a6
Revises: f9ab0648f636
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'f9ab0648f636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('position', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('manager_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_position'), ['position'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_manager_id'), ['manager_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_users_manager_id_users', 'users', ['manager_id'], ['id']
        )

    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('department_head_user_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_departments_department_head_user_id'),
            ['department_head_user_id'],
            unique=False,
        )
        batch_op.create_foreign_key(
            'fk_departments_department_head_user_id_users',
            'users',
            ['department_head_user_id'],
            ['id'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_departments_department_head_user_id_users', type_='foreignkey'
        )
        batch_op.drop_index(batch_op.f('ix_departments_department_head_user_id'))
        batch_op.drop_column('department_head_user_id')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_manager_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_users_manager_id'))
        batch_op.drop_index(batch_op.f('ix_users_position'))
        batch_op.drop_column('manager_id')
        batch_op.drop_column('position')
