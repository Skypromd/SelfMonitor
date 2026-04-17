"""cis record reconciliation + task reminder_meta

Revision ID: f8d3e1000002
Revises: e7c2f9000001
Create Date: 2026-04-17 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8d3e1000002"
down_revision: Union[str, None] = "e7c2f9000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cis_records",
        sa.Column("reconciliation_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "cis_records",
        sa.Column("bank_net_observed_gbp", sa.Float(), nullable=True),
    )
    op.add_column(
        "cis_review_tasks",
        sa.Column("reminder_meta", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cis_review_tasks", "reminder_meta")
    op.drop_column("cis_records", "bank_net_observed_gbp")
    op.drop_column("cis_records", "reconciliation_status")
