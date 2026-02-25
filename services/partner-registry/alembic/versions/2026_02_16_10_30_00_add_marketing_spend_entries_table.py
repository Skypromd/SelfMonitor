"""add marketing spend entries table

Revision ID: b9e8d7c6f5a4
Revises: a7d4f8c1b2e9
Create Date: 2026-02-16 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9e8d7c6f5a4"
down_revision: Union[str, None] = "a7d4f8c1b2e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_spend_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("month_start", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("spend_gbp", sa.Float(), nullable=False),
        sa.Column("acquired_customers", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_marketing_spend_entries_spend_non_negative",
        "marketing_spend_entries",
        "spend_gbp >= 0",
    )
    op.create_check_constraint(
        "ck_marketing_spend_entries_acquired_customers_non_negative",
        "marketing_spend_entries",
        "acquired_customers >= 0",
    )
    op.create_index(op.f("ix_marketing_spend_entries_id"), "marketing_spend_entries", ["id"], unique=False)
    op.create_index(
        op.f("ix_marketing_spend_entries_created_by_user_id"),
        "marketing_spend_entries",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_marketing_spend_entries_created_at"), "marketing_spend_entries", ["created_at"], unique=False)
    op.create_index("ix_marketing_spend_entries_month_start", "marketing_spend_entries", ["month_start"], unique=False)
    op.create_index("ix_marketing_spend_entries_channel", "marketing_spend_entries", ["channel"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_marketing_spend_entries_channel", table_name="marketing_spend_entries")
    op.drop_index("ix_marketing_spend_entries_month_start", table_name="marketing_spend_entries")
    op.drop_index(op.f("ix_marketing_spend_entries_created_at"), table_name="marketing_spend_entries")
    op.drop_index(op.f("ix_marketing_spend_entries_created_by_user_id"), table_name="marketing_spend_entries")
    op.drop_index(op.f("ix_marketing_spend_entries_id"), table_name="marketing_spend_entries")
    op.drop_constraint(
        "ck_marketing_spend_entries_acquired_customers_non_negative",
        "marketing_spend_entries",
        type_="check",
    )
    op.drop_constraint(
        "ck_marketing_spend_entries_spend_non_negative",
        "marketing_spend_entries",
        type_="check",
    )
    op.drop_table("marketing_spend_entries")
