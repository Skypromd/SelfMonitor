"""Stripe payment link columns and webhook dedup table

Revision ID: 002_stripe_invoice_payment_links
Revises: 001_initial_invoice_schema
Create Date: 2026-04-20

"""
from alembic import op
import sqlalchemy as sa

revision = "002_stripe_invoice_payment_links"
down_revision = "001_initial_invoice_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("stripe_payment_link_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("stripe_payment_link_url", sa.Text(), nullable=True),
    )
    op.create_table(
        "stripe_invoice_webhook_events",
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("stripe_invoice_webhook_events")
    op.drop_column("invoices", "stripe_payment_link_url")
    op.drop_column("invoices", "stripe_payment_link_id")
