"""add receipt reconcile metadata columns

Revision ID: c4b1f728a9d1
Revises: 08855e9668d2
Create Date: 2026-02-13 15:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4b1f728a9d1"
down_revision: Union[str, None] = "08855e9668d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("reconciliation_status", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("ignored_candidate_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "ignored_candidate_ids")
    op.drop_column("transactions", "reconciliation_status")
