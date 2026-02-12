"""create partner registry tables

Revision ID: a1c9b3f2e4d7
Revises:
Create Date: 2026-02-12 18:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c9b3f2e4d7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "partners",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("services_offered", sa.JSON(), nullable=False),
        sa.Column("website", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_partners_id"), "partners", ["id"], unique=False)
    op.create_index(op.f("ix_partners_name"), "partners", ["name"], unique=False)

    op.create_table(
        "handoff_leads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("partner_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_handoff_leads_created_at"), "handoff_leads", ["created_at"], unique=False)
    op.create_index(op.f("ix_handoff_leads_id"), "handoff_leads", ["id"], unique=False)
    op.create_index(op.f("ix_handoff_leads_partner_id"), "handoff_leads", ["partner_id"], unique=False)
    op.create_index(op.f("ix_handoff_leads_user_id"), "handoff_leads", ["user_id"], unique=False)
    op.create_index("ix_handoff_leads_partner_created_at", "handoff_leads", ["partner_id", "created_at"], unique=False)
    op.create_index(
        "ix_handoff_leads_user_partner_created_at",
        "handoff_leads",
        ["user_id", "partner_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_handoff_leads_user_partner_created_at", table_name="handoff_leads")
    op.drop_index("ix_handoff_leads_partner_created_at", table_name="handoff_leads")
    op.drop_index(op.f("ix_handoff_leads_user_id"), table_name="handoff_leads")
    op.drop_index(op.f("ix_handoff_leads_partner_id"), table_name="handoff_leads")
    op.drop_index(op.f("ix_handoff_leads_id"), table_name="handoff_leads")
    op.drop_index(op.f("ix_handoff_leads_created_at"), table_name="handoff_leads")
    op.drop_table("handoff_leads")

    op.drop_index(op.f("ix_partners_name"), table_name="partners")
    op.drop_index(op.f("ix_partners_id"), table_name="partners")
    op.drop_table("partners")
