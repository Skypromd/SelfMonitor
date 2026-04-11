"""Add file_size_bytes to documents for storage quota accounting.

Revision ID: b2c3d4e5f6a8
Revises: 8a7c6f2a1b3d
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "8a7c6f2a1b3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "file_size_bytes")
