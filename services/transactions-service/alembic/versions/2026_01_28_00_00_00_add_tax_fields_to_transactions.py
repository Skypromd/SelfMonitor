"""Add tax fields to transactions

Revision ID: 9e1a0c7d7f44
Revises: 08855e9668d2
Create Date: 2026-01-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e1a0c7d7f44"
down_revision: Union[str, None] = "08855e9668d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("tax_category", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("business_use_percent", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "business_use_percent")
    op.drop_column("transactions", "tax_category")
