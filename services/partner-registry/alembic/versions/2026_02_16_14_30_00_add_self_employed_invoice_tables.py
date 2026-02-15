"""add self employed invoice tables

Revision ID: c2f7d9a1e4b6
Revises: b9e8d7c6f5a4
Create Date: 2026-02-16 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2f7d9a1e4b6"
down_revision: Union[str, None] = "b9e8d7c6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "self_employed_invoices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("invoice_number", sa.String(length=32), nullable=False),
        sa.Column("customer_name", sa.String(length=180), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_address", sa.String(length=500), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_gbp", sa.Float(), nullable=False),
        sa.Column("tax_rate_percent", sa.Float(), nullable=False),
        sa.Column("tax_amount_gbp", sa.Float(), nullable=False),
        sa.Column("total_amount_gbp", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_self_employed_invoices_status_allowed",
        "self_employed_invoices",
        "status IN ('draft', 'issued', 'paid', 'overdue', 'void')",
    )
    op.create_check_constraint(
        "ck_self_employed_invoices_tax_rate",
        "self_employed_invoices",
        "tax_rate_percent >= 0 AND tax_rate_percent <= 100",
    )
    op.create_check_constraint(
        "ck_self_employed_invoices_subtotal_non_negative",
        "self_employed_invoices",
        "subtotal_gbp >= 0",
    )
    op.create_check_constraint(
        "ck_self_employed_invoices_tax_amount_non_negative",
        "self_employed_invoices",
        "tax_amount_gbp >= 0",
    )
    op.create_check_constraint(
        "ck_self_employed_invoices_total_non_negative",
        "self_employed_invoices",
        "total_amount_gbp >= 0",
    )
    op.create_index(op.f("ix_self_employed_invoices_id"), "self_employed_invoices", ["id"], unique=False)
    op.create_index(op.f("ix_self_employed_invoices_user_id"), "self_employed_invoices", ["user_id"], unique=False)
    op.create_index("ix_self_employed_invoices_user_id_created_at", "self_employed_invoices", ["user_id", "created_at"], unique=False)
    op.create_index("ix_self_employed_invoices_status", "self_employed_invoices", ["status"], unique=False)
    op.create_index("ix_self_employed_invoices_due_date", "self_employed_invoices", ["due_date"], unique=False)
    op.create_index("ix_self_employed_invoices_invoice_number", "self_employed_invoices", ["invoice_number"], unique=True)

    op.create_table(
        "self_employed_invoice_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("invoice_id", sa.String(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price_gbp", sa.Float(), nullable=False),
        sa.Column("line_total_gbp", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["self_employed_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_self_employed_invoice_lines_quantity_positive",
        "self_employed_invoice_lines",
        "quantity > 0",
    )
    op.create_check_constraint(
        "ck_self_employed_invoice_lines_unit_price_non_negative",
        "self_employed_invoice_lines",
        "unit_price_gbp >= 0",
    )
    op.create_check_constraint(
        "ck_self_employed_invoice_lines_line_total_non_negative",
        "self_employed_invoice_lines",
        "line_total_gbp >= 0",
    )
    op.create_index(op.f("ix_self_employed_invoice_lines_id"), "self_employed_invoice_lines", ["id"], unique=False)
    op.create_index("ix_self_employed_invoice_lines_invoice_id", "self_employed_invoice_lines", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_self_employed_invoice_lines_invoice_id", table_name="self_employed_invoice_lines")
    op.drop_index(op.f("ix_self_employed_invoice_lines_id"), table_name="self_employed_invoice_lines")
    op.drop_constraint(
        "ck_self_employed_invoice_lines_line_total_non_negative",
        "self_employed_invoice_lines",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_invoice_lines_unit_price_non_negative",
        "self_employed_invoice_lines",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_invoice_lines_quantity_positive",
        "self_employed_invoice_lines",
        type_="check",
    )
    op.drop_table("self_employed_invoice_lines")

    op.drop_index("ix_self_employed_invoices_invoice_number", table_name="self_employed_invoices")
    op.drop_index("ix_self_employed_invoices_due_date", table_name="self_employed_invoices")
    op.drop_index("ix_self_employed_invoices_status", table_name="self_employed_invoices")
    op.drop_index("ix_self_employed_invoices_user_id_created_at", table_name="self_employed_invoices")
    op.drop_index(op.f("ix_self_employed_invoices_user_id"), table_name="self_employed_invoices")
    op.drop_index(op.f("ix_self_employed_invoices_id"), table_name="self_employed_invoices")
    op.drop_constraint(
        "ck_self_employed_invoices_total_non_negative",
        "self_employed_invoices",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_invoices_tax_amount_non_negative",
        "self_employed_invoices",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_invoices_subtotal_non_negative",
        "self_employed_invoices",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_invoices_tax_rate",
        "self_employed_invoices",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_invoices_status_allowed",
        "self_employed_invoices",
        type_="check",
    )
    op.drop_table("self_employed_invoices")
