"""cis_obligations per tax month x contractor

Revision ID: a9e4f2000003
Revises: f8d3e1000002
Create Date: 2026-04-17 23:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9e4f2000003"
down_revision: Union[str, None] = "f8d3e1000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cis_obligations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("cis_tax_month_label", sa.String(length=32), nullable=False),
        sa.Column("contractor_key", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'MISSING'"),
        ),
        sa.Column("snooze_until", sa.Date(), nullable=True),
        sa.Column("last_reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "cis_tax_month_label",
            "contractor_key",
            name="uq_cis_obligation_user_month_contractor",
        ),
    )
    op.create_index("ix_cis_obligations_user_id", "cis_obligations", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cis_obligations_user_id", table_name="cis_obligations")
    op.drop_table("cis_obligations")
