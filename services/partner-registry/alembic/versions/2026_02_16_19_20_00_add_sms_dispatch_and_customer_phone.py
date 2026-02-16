"""add sms reminder channel and customer phone fields

Revision ID: e8f1a2b3c4d5
Revises: d5a2c4b7e9f1
Create Date: 2026-02-16 19:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "d5a2c4b7e9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("self_employed_invoices", sa.Column("customer_phone", sa.String(length=32), nullable=True))
    op.add_column("self_employed_recurring_invoice_plans", sa.Column("customer_phone", sa.String(length=32), nullable=True))

    op.drop_constraint("ck_self_employed_invoice_reminders_channel", "self_employed_invoice_reminders", type_="check")
    op.create_check_constraint(
        "ck_self_employed_invoice_reminders_channel",
        "self_employed_invoice_reminders",
        "channel IN ('email', 'sms', 'in_app')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_self_employed_invoice_reminders_channel", "self_employed_invoice_reminders", type_="check")
    op.create_check_constraint(
        "ck_self_employed_invoice_reminders_channel",
        "self_employed_invoice_reminders",
        "channel IN ('email', 'in_app')",
    )

    op.drop_column("self_employed_recurring_invoice_plans", "customer_phone")
    op.drop_column("self_employed_invoices", "customer_phone")
