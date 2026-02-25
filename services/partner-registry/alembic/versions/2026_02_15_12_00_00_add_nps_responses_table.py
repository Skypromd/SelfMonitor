"""add nps responses table

Revision ID: a7d4f8c1b2e9
Revises: f0e4a1c2d3b4
Create Date: 2026-02-15 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7d4f8c1b2e9"
down_revision: Union[str, None] = "f0e4a1c2d3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nps_responses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.String(), nullable=True),
        sa.Column("context_tag", sa.String(length=64), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_nps_responses_score_range",
        "nps_responses",
        "score >= 0 AND score <= 10",
    )
    op.create_index(op.f("ix_nps_responses_id"), "nps_responses", ["id"], unique=False)
    op.create_index(op.f("ix_nps_responses_user_id"), "nps_responses", ["user_id"], unique=False)
    op.create_index("ix_nps_responses_created_at", "nps_responses", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nps_responses_created_at", table_name="nps_responses")
    op.drop_index(op.f("ix_nps_responses_user_id"), table_name="nps_responses")
    op.drop_index(op.f("ix_nps_responses_id"), table_name="nps_responses")
    op.drop_constraint("ck_nps_responses_score_range", "nps_responses", type_="check")
    op.drop_table("nps_responses")
