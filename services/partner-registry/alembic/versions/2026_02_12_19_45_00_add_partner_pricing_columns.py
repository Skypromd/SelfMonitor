"""add partner pricing columns

Revision ID: c3d2e5b9f8a1
Revises: b7f4d2a9c1e6
Create Date: 2026-02-12 19:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d2e5b9f8a1"
down_revision: Union[str, None] = "b7f4d2a9c1e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "partners",
        sa.Column("qualified_lead_fee_gbp", sa.Float(), nullable=False, server_default=sa.text("12.0")),
    )
    op.add_column(
        "partners",
        sa.Column("converted_lead_fee_gbp", sa.Float(), nullable=False, server_default=sa.text("35.0")),
    )


def downgrade() -> None:
    op.drop_column("partners", "converted_lead_fee_gbp")
    op.drop_column("partners", "qualified_lead_fee_gbp")
