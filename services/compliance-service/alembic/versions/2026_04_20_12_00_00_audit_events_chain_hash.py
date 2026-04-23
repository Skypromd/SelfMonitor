"""audit_events: per-user hash chain columns

Revision ID: c3d4e5f6a7b8
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("prev_chain_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("chain_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_events", "chain_hash")
    op.drop_column("audit_events", "prev_chain_hash")
