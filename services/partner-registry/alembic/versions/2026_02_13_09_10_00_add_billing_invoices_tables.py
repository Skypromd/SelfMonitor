"""add billing invoices tables

Revision ID: d9b5c1f7a2e4
Revises: c3d2e5b9f8a1
Create Date: 2026-02-13 09:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9b5c1f7a2e4"
down_revision: Union[str, None] = "c3d2e5b9f8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("generated_by_user_id", sa.String(), nullable=False),
        sa.Column("partner_id", sa.String(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("statuses", sa.JSON(), nullable=False),
        sa.Column("total_amount_gbp", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_billing_invoices_status_allowed",
        "billing_invoices",
        "status IN ('generated', 'issued', 'paid', 'void')",
    )
    op.create_index(op.f("ix_billing_invoices_id"), "billing_invoices", ["id"], unique=False)
    op.create_index("ix_billing_invoices_created_at", "billing_invoices", ["created_at"], unique=False)
    op.create_index("ix_billing_invoices_status", "billing_invoices", ["status"], unique=False)
    op.create_index(op.f("ix_billing_invoices_generated_by_user_id"), "billing_invoices", ["generated_by_user_id"], unique=False)
    op.create_index(op.f("ix_billing_invoices_partner_id"), "billing_invoices", ["partner_id"], unique=False)

    op.create_table(
        "billing_invoice_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("invoice_id", sa.String(), nullable=False),
        sa.Column("partner_id", sa.String(), nullable=False),
        sa.Column("partner_name", sa.String(), nullable=False),
        sa.Column("qualified_leads", sa.Integer(), nullable=False),
        sa.Column("converted_leads", sa.Integer(), nullable=False),
        sa.Column("unique_users", sa.Integer(), nullable=False),
        sa.Column("qualified_lead_fee_gbp", sa.Float(), nullable=False),
        sa.Column("converted_lead_fee_gbp", sa.Float(), nullable=False),
        sa.Column("amount_gbp", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["billing_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_billing_invoice_lines_id"), "billing_invoice_lines", ["id"], unique=False)
    op.create_index("ix_billing_invoice_lines_invoice_id", "billing_invoice_lines", ["invoice_id"], unique=False)
    op.create_index("ix_billing_invoice_lines_partner_id", "billing_invoice_lines", ["partner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_invoice_lines_partner_id", table_name="billing_invoice_lines")
    op.drop_index("ix_billing_invoice_lines_invoice_id", table_name="billing_invoice_lines")
    op.drop_index(op.f("ix_billing_invoice_lines_id"), table_name="billing_invoice_lines")
    op.drop_table("billing_invoice_lines")

    op.drop_index(op.f("ix_billing_invoices_partner_id"), table_name="billing_invoices")
    op.drop_index(op.f("ix_billing_invoices_generated_by_user_id"), table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_status", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_created_at", table_name="billing_invoices")
    op.drop_index(op.f("ix_billing_invoices_id"), table_name="billing_invoices")
    op.drop_constraint("ck_billing_invoices_status_allowed", "billing_invoices", type_="check")
    op.drop_table("billing_invoices")
