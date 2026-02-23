"""Add subscription fields to user profiles

Revision ID: 6c4b7e5c0a21
Revises: d41a1b87042c
Create Date: 2026-01-28 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c4b7e5c0a21"
down_revision: Union[str, None] = "d41a1b87042c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("subscription_plan", sa.String(), server_default="free", nullable=False))
    op.add_column("user_profiles", sa.Column("subscription_status", sa.String(), server_default="active", nullable=False))
    op.add_column("user_profiles", sa.Column("billing_cycle", sa.String(), server_default="monthly", nullable=False))
    op.add_column("user_profiles", sa.Column("current_period_start", sa.Date(), nullable=True))
    op.add_column("user_profiles", sa.Column("current_period_end", sa.Date(), nullable=True))
    op.add_column("user_profiles", sa.Column("monthly_close_day", sa.Integer(), server_default="1", nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "monthly_close_day")
    op.drop_column("user_profiles", "current_period_end")
    op.drop_column("user_profiles", "current_period_start")
    op.drop_column("user_profiles", "billing_cycle")
    op.drop_column("user_profiles", "subscription_status")
    op.drop_column("user_profiles", "subscription_plan")
