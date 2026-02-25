"""add self employed calendar events and reminders

Revision ID: f3b9d2e1a7c4
Revises: e8f1a2b3c4d5
Create Date: 2026-02-17 09:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b9d2e1a7c4"
down_revision: Union[str, None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "self_employed_calendar_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("recipient_name", sa.String(length=180), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("recipient_phone", sa.String(length=32), nullable=True),
        sa.Column("notify_in_app", sa.Integer(), nullable=False),
        sa.Column("notify_email", sa.Integer(), nullable=False),
        sa.Column("notify_sms", sa.Integer(), nullable=False),
        sa.Column("notify_before_minutes", sa.Integer(), nullable=False),
        sa.Column("reminder_last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_events_status",
        "self_employed_calendar_events",
        "status IN ('scheduled', 'completed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_events_notify_before_minutes",
        "self_employed_calendar_events",
        "notify_before_minutes >= 0 AND notify_before_minutes <= 10080",
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_events_notify_in_app",
        "self_employed_calendar_events",
        "notify_in_app IN (0, 1)",
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_events_notify_email",
        "self_employed_calendar_events",
        "notify_email IN (0, 1)",
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_events_notify_sms",
        "self_employed_calendar_events",
        "notify_sms IN (0, 1)",
    )
    op.create_index(
        op.f("ix_self_employed_calendar_events_id"),
        "self_employed_calendar_events",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_self_employed_calendar_events_user_id"),
        "self_employed_calendar_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_self_employed_calendar_events_starts_at"),
        "self_employed_calendar_events",
        ["starts_at"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_calendar_events_user_starts_at",
        "self_employed_calendar_events",
        ["user_id", "starts_at"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_calendar_events_status",
        "self_employed_calendar_events",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_calendar_events_reminder_last_sent_at",
        "self_employed_calendar_events",
        ["reminder_last_sent_at"],
        unique=False,
    )

    op.create_table(
        "self_employed_calendar_reminders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("reminder_type", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["self_employed_calendar_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_reminders_type",
        "self_employed_calendar_reminders",
        "reminder_type IN ('upcoming', 'overdue')",
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_reminders_channel",
        "self_employed_calendar_reminders",
        "channel IN ('email', 'sms', 'in_app')",
    )
    op.create_check_constraint(
        "ck_self_employed_calendar_reminders_status",
        "self_employed_calendar_reminders",
        "status IN ('queued', 'sent', 'failed')",
    )
    op.create_index(
        op.f("ix_self_employed_calendar_reminders_id"),
        "self_employed_calendar_reminders",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_self_employed_calendar_reminders_user_id"),
        "self_employed_calendar_reminders",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_calendar_reminders_event_id",
        "self_employed_calendar_reminders",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_self_employed_calendar_reminders_user_id_created_at",
        "self_employed_calendar_reminders",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_self_employed_calendar_reminders_user_id_created_at", table_name="self_employed_calendar_reminders")
    op.drop_index("ix_self_employed_calendar_reminders_event_id", table_name="self_employed_calendar_reminders")
    op.drop_index(op.f("ix_self_employed_calendar_reminders_user_id"), table_name="self_employed_calendar_reminders")
    op.drop_index(op.f("ix_self_employed_calendar_reminders_id"), table_name="self_employed_calendar_reminders")
    op.drop_constraint("ck_self_employed_calendar_reminders_status", "self_employed_calendar_reminders", type_="check")
    op.drop_constraint("ck_self_employed_calendar_reminders_channel", "self_employed_calendar_reminders", type_="check")
    op.drop_constraint("ck_self_employed_calendar_reminders_type", "self_employed_calendar_reminders", type_="check")
    op.drop_table("self_employed_calendar_reminders")

    op.drop_index("ix_self_employed_calendar_events_reminder_last_sent_at", table_name="self_employed_calendar_events")
    op.drop_index("ix_self_employed_calendar_events_status", table_name="self_employed_calendar_events")
    op.drop_index("ix_self_employed_calendar_events_user_starts_at", table_name="self_employed_calendar_events")
    op.drop_index(op.f("ix_self_employed_calendar_events_starts_at"), table_name="self_employed_calendar_events")
    op.drop_index(op.f("ix_self_employed_calendar_events_user_id"), table_name="self_employed_calendar_events")
    op.drop_index(op.f("ix_self_employed_calendar_events_id"), table_name="self_employed_calendar_events")
    op.drop_constraint("ck_self_employed_calendar_events_notify_sms", "self_employed_calendar_events", type_="check")
    op.drop_constraint("ck_self_employed_calendar_events_notify_email", "self_employed_calendar_events", type_="check")
    op.drop_constraint("ck_self_employed_calendar_events_notify_in_app", "self_employed_calendar_events", type_="check")
    op.drop_constraint(
        "ck_self_employed_calendar_events_notify_before_minutes",
        "self_employed_calendar_events",
        type_="check",
    )
    op.drop_constraint("ck_self_employed_calendar_events_status", "self_employed_calendar_events", type_="check")
    op.drop_table("self_employed_calendar_events")
