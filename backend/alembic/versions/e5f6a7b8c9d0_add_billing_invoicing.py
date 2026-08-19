"""add invoices, invoice line items, and billing rate fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(12, 2), nullable=False),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('created_by_email', sa.String(length=255), nullable=False),
        sa.Column('created_by_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invoices_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invoices_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invoices_contract_id'), ['contract_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invoices_invoice_number'), ['invoice_number'], unique=True)
        batch_op.create_index(batch_op.f('ix_invoices_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_invoices_deleted_at'), ['deleted_at'], unique=False)

    op.create_table(
        'invoice_line_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('rate', sa.Numeric(10, 2), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('invoice_line_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invoice_line_items_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invoice_line_items_invoice_id'), ['invoice_id'], unique=False)

    with op.batch_alter_table('time_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invoice_line_item_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_time_entries_invoice_line_item_id'), ['invoice_line_item_id'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_time_entries_invoice_line_item_id_invoice_line_items',
            'invoice_line_items',
            ['invoice_line_item_id'],
            ['id'],
        )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('standard_billing_rate', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('standard_billing_rate')

    with op.batch_alter_table('time_entries', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_time_entries_invoice_line_item_id_invoice_line_items', type_='foreignkey'
        )
        batch_op.drop_index(batch_op.f('ix_time_entries_invoice_line_item_id'))
        batch_op.drop_column('invoice_line_item_id')

    with op.batch_alter_table('invoice_line_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invoice_line_items_invoice_id'))
        batch_op.drop_index(batch_op.f('ix_invoice_line_items_id'))
    op.drop_table('invoice_line_items')

    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invoices_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_invoices_status'))
        batch_op.drop_index(batch_op.f('ix_invoices_invoice_number'))
        batch_op.drop_index(batch_op.f('ix_invoices_contract_id'))
        batch_op.drop_index(batch_op.f('ix_invoices_project_id'))
        batch_op.drop_index(batch_op.f('ix_invoices_id'))
    op.drop_table('invoices')
