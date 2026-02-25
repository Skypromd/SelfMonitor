"""Initial invoice service schema

Revision ID: 001_initial_invoice_schema
Revises: 
Create Date: 2026-02-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_invoice_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE invoice_status AS ENUM ('draft', 'sent', 'paid', 'partially_paid', 'overdue', 'cancelled')")
    op.execute("CREATE TYPE payment_method AS ENUM ('bank_transfer', 'card', 'cash', 'paypal', 'stripe', 'other')")
    op.execute("CREATE TYPE frequency_type AS ENUM ('weekly', 'monthly', 'quarterly', 'yearly')")
    
    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('company_id', sa.String(36), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('client_name', sa.String(200), nullable=False),
        sa.Column('client_email', sa.String(200), nullable=True),
        sa.Column('client_address', sa.Text(), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('payment_terms', sa.Integer(), nullable=True),
        sa.Column('po_number', sa.String(100), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, default=0),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False, default=0),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(precision=12, scale=2), nullable=True, default=0),
        sa.Column('discount_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=True, default=0),
        sa.Column('currency', sa.String(3), nullable=False, default='GBP'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('pdf_file_path', sa.String(500), nullable=True),
        sa.Column('status', postgresql.ENUM('draft', 'sent', 'paid', 'partially_paid', 'overdue', 'cancelled', name='invoice_status'), nullable=False, default='draft'),  # type: ignore
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('idx_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('idx_invoices_client_name', 'invoices', ['client_name'])
    op.create_index('idx_invoices_status', 'invoices', ['status'])
    op.create_index('idx_invoices_invoice_date', 'invoices', ['invoice_date'])
    
    # Create invoice_line_items table
    op.create_table('invoice_line_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=False, default=1),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE')
    )
    op.create_index('idx_line_items_invoice_id', 'invoice_line_items', ['invoice_id'])
    op.create_index('idx_line_items_category', 'invoice_line_items', ['category'])
    
    # Create invoice_payments table
    op.create_table('invoice_payments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_method', postgresql.ENUM('bank_transfer', 'card', 'cash', 'paypal', 'stripe', 'other', name='payment_method'), nullable=False),  # type: ignore
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE')
    )
    op.create_index('idx_payments_invoice_id', 'invoice_payments', ['invoice_id'])
    op.create_index('idx_payments_payment_date', 'invoice_payments', ['payment_date'])
    
    # Create invoice_templates table
    op.create_table('invoice_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),  # NULL for system templates
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.String(50), nullable=False),
        sa.Column('template_content', sa.Text(), nullable=True),
        sa.Column('default_line_items', sa.JSON(), nullable=True),
        sa.Column('company_details', sa.JSON(), nullable=True),
        sa.Column('styling_options', sa.JSON(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_system_template', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_templates_user_id', 'invoice_templates', ['user_id'])
    op.create_index('idx_templates_template_type', 'invoice_templates', ['template_type'])
    op.create_index('idx_templates_is_system', 'invoice_templates', ['is_system_template'])
    
    # Create recurring_invoices table
    op.create_table('recurring_invoices',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('frequency', postgresql.ENUM('weekly', 'monthly', 'quarterly', 'yearly', name='frequency_type'), nullable=False),  # type: ignore
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('next_invoice_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('auto_send', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['invoice_templates.id'], ondelete='CASCADE')
    )
    op.create_index('idx_recurring_user_id', 'recurring_invoices', ['user_id'])
    op.create_index('idx_recurring_next_date', 'recurring_invoices', ['next_invoice_date'])
    op.create_index('idx_recurring_is_active', 'recurring_invoices', ['is_active'])
    

def downgrade() -> None:
    # Drop tables
    op.drop_table('recurring_invoices')
    op.drop_table('invoice_templates')
    op.drop_table('invoice_payments')
    op.drop_table('invoice_line_items')
    op.drop_table('invoices')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS frequency_type")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS invoice_status")