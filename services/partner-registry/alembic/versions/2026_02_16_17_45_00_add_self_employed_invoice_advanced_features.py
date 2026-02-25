"""add self employed invoicing advanced features

Revision ID: d5a2c4b7e9f1
Revises: c2f7d9a1e4b6
Create Date: 2026-02-16 17:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5a2c4b7e9f1"
down_revision: Union[str, None] = "c2f7d9a1e4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "self_employed_invoice_brand_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("business_name", sa.String(length=180), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("accent_color", sa.String(length=16), nullable=True),
        sa.Column("payment_terms_note", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_self_employed_invoice_brand_profiles_user_id",
        "self_employed_invoice_brand_profiles",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_self_employed_invoice_brand_profiles_id"),
        "self_employed_invoice_brand_profiles",
        ["id"],
        unique=False,
    )

    op.create_table(
        "self_employed_recurring_invoice_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("customer_name", sa.String(length=180), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_address", sa.String(length=500), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("tax_rate_percent", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("cadence", sa.String(length=16), nullable=False),
        sa.Column("next_issue_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False),
        sa.Column("last_generated_invoice_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_self_employed_recurring_invoice_plans_cadence",
        "self_employed_recurring_invoice_plans",
        "cadence IN ('weekly', 'monthly', 'quarterly')",
    )
    op.create_check_constraint(
        "ck_self_employed_recurring_invoice_plans_tax_rate",
        "self_employed_recurring_invoice_plans",
        "tax_rate_percent >= 0 AND tax_rate_percent <= 100",
    )
    op.create_index(
        "ix_self_employed_recurring_invoice_plans_user_id",
        "self_employed_recurring_invoice_plans",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_recurring_invoice_plans_next_issue_date",
        "self_employed_recurring_invoice_plans",
        ["next_issue_date"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_recurring_invoice_plans_active",
        "self_employed_recurring_invoice_plans",
        ["active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_self_employed_recurring_invoice_plans_id"),
        "self_employed_recurring_invoice_plans",
        ["id"],
        unique=False,
    )

    op.add_column("self_employed_invoices", sa.Column("payment_link_url", sa.String(length=500), nullable=True))
    op.add_column("self_employed_invoices", sa.Column("payment_link_provider", sa.String(length=64), nullable=True))
    op.add_column("self_employed_invoices", sa.Column("recurring_plan_id", sa.String(), nullable=True))
    op.add_column("self_employed_invoices", sa.Column("brand_business_name", sa.String(length=180), nullable=True))
    op.add_column("self_employed_invoices", sa.Column("brand_logo_url", sa.String(length=500), nullable=True))
    op.add_column("self_employed_invoices", sa.Column("brand_accent_color", sa.String(length=16), nullable=True))
    op.add_column("self_employed_invoices", sa.Column("reminder_last_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_self_employed_invoices_recurring_plan_id",
        "self_employed_invoices",
        ["recurring_plan_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_self_employed_invoices_recurring_plan_id",
        "self_employed_invoices",
        "self_employed_recurring_invoice_plans",
        ["recurring_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "self_employed_invoice_reminders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("invoice_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("reminder_type", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["self_employed_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_self_employed_invoice_reminders_type",
        "self_employed_invoice_reminders",
        "reminder_type IN ('due_soon', 'overdue')",
    )
    op.create_check_constraint(
        "ck_self_employed_invoice_reminders_channel",
        "self_employed_invoice_reminders",
        "channel IN ('email', 'in_app')",
    )
    op.create_check_constraint(
        "ck_self_employed_invoice_reminders_status",
        "self_employed_invoice_reminders",
        "status IN ('queued', 'sent', 'failed')",
    )
    op.create_index(
        "ix_self_employed_invoice_reminders_invoice_id",
        "self_employed_invoice_reminders",
        ["invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_invoice_reminders_user_id_created_at",
        "self_employed_invoice_reminders",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_self_employed_invoice_reminders_id"),
        "self_employed_invoice_reminders",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_self_employed_invoice_reminders_id"), table_name="self_employed_invoice_reminders")
    op.drop_index("ix_self_employed_invoice_reminders_user_id_created_at", table_name="self_employed_invoice_reminders")
    op.drop_index("ix_self_employed_invoice_reminders_invoice_id", table_name="self_employed_invoice_reminders")
    op.drop_constraint("ck_self_employed_invoice_reminders_status", "self_employed_invoice_reminders", type_="check")
    op.drop_constraint("ck_self_employed_invoice_reminders_channel", "self_employed_invoice_reminders", type_="check")
    op.drop_constraint("ck_self_employed_invoice_reminders_type", "self_employed_invoice_reminders", type_="check")
    op.drop_table("self_employed_invoice_reminders")

    op.drop_constraint("fk_self_employed_invoices_recurring_plan_id", "self_employed_invoices", type_="foreignkey")
    op.drop_index("ix_self_employed_invoices_recurring_plan_id", table_name="self_employed_invoices")
    op.drop_column("self_employed_invoices", "reminder_last_sent_at")
    op.drop_column("self_employed_invoices", "brand_accent_color")
    op.drop_column("self_employed_invoices", "brand_logo_url")
    op.drop_column("self_employed_invoices", "brand_business_name")
    op.drop_column("self_employed_invoices", "recurring_plan_id")
    op.drop_column("self_employed_invoices", "payment_link_provider")
    op.drop_column("self_employed_invoices", "payment_link_url")

    op.drop_index(op.f("ix_self_employed_recurring_invoice_plans_id"), table_name="self_employed_recurring_invoice_plans")
    op.drop_index("ix_self_employed_recurring_invoice_plans_active", table_name="self_employed_recurring_invoice_plans")
    op.drop_index("ix_self_employed_recurring_invoice_plans_next_issue_date", table_name="self_employed_recurring_invoice_plans")
    op.drop_index("ix_self_employed_recurring_invoice_plans_user_id", table_name="self_employed_recurring_invoice_plans")
    op.drop_constraint(
        "ck_self_employed_recurring_invoice_plans_tax_rate",
        "self_employed_recurring_invoice_plans",
        type_="check",
    )
    op.drop_constraint(
        "ck_self_employed_recurring_invoice_plans_cadence",
        "self_employed_recurring_invoice_plans",
        type_="check",
    )
    op.drop_table("self_employed_recurring_invoice_plans")

    op.drop_index(op.f("ix_self_employed_invoice_brand_profiles_id"), table_name="self_employed_invoice_brand_profiles")
    op.drop_index("ix_self_employed_invoice_brand_profiles_user_id", table_name="self_employed_invoice_brand_profiles")
    op.drop_table("self_employed_invoice_brand_profiles")
