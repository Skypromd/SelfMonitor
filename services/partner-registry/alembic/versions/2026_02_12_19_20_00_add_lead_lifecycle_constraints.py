"""add lead lifecycle constraints

Revision ID: b7f4d2a9c1e6
Revises: a1c9b3f2e4d7
Create Date: 2026-02-12 19:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f4d2a9c1e6"
down_revision: Union[str, None] = "a1c9b3f2e4d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "handoff_leads",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_handoff_leads_status", "handoff_leads", ["status"], unique=False)
    op.create_check_constraint(
        "ck_handoff_leads_status_allowed",
        "handoff_leads",
        "status IN ('initiated', 'qualified', 'rejected', 'converted')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_handoff_leads_status_allowed", "handoff_leads", type_="check")
    op.drop_index("ix_handoff_leads_status", table_name="handoff_leads")
    op.drop_column("handoff_leads", "updated_at")
