"""add invoice number and due date

Revision ID: f0e4a1c2d3b4
Revises: d9b5c1f7a2e4
Create Date: 2026-02-13 11:30:00.000000

"""

import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f0e4a1c2d3b4"
down_revision: Union[str, None] = "d9b5c1f7a2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _to_date(value: object) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return datetime.datetime.now(datetime.UTC).date()
    return datetime.datetime.now(datetime.UTC).date()


def upgrade() -> None:
    op.add_column("billing_invoices", sa.Column("invoice_number", sa.String(length=32), nullable=True))
    op.add_column("billing_invoices", sa.Column("due_date", sa.Date(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, created_at FROM billing_invoices ORDER BY created_at ASC, id ASC")
    ).mappings()

    sequence_by_prefix: dict[str, int] = {}
    for row in rows:
        created_date = _to_date(row.get("created_at"))
        prefix = f"INV-{created_date.strftime('%Y%m')}"
        next_seq = sequence_by_prefix.get(prefix, 0) + 1
        sequence_by_prefix[prefix] = next_seq
        invoice_number = f"{prefix}-{next_seq:06d}"
        due_date = created_date + datetime.timedelta(days=14)
        connection.execute(
            sa.text(
                "UPDATE billing_invoices "
                "SET invoice_number = :invoice_number, due_date = :due_date "
                "WHERE id = :invoice_id"
            ),
            {
                "invoice_number": invoice_number,
                "due_date": due_date,
                "invoice_id": row.get("id"),
            },
        )

    op.alter_column("billing_invoices", "invoice_number", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("billing_invoices", "due_date", existing_type=sa.Date(), nullable=False)
    op.create_index("ix_billing_invoices_invoice_number", "billing_invoices", ["invoice_number"], unique=True)
    op.create_index("ix_billing_invoices_due_date", "billing_invoices", ["due_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_invoices_due_date", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_invoice_number", table_name="billing_invoices")
    op.drop_column("billing_invoices", "due_date")
    op.drop_column("billing_invoices", "invoice_number")
