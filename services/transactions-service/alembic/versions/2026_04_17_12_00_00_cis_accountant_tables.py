"""cis records, review tasks, accountant delegations

Revision ID: e7c2f9000001
Revises: c4b1f728a9d1
Create Date: 2026-04-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7c2f9000001"
down_revision: Union[str, None] = "c4b1f728a9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cis_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("contractor_name", sa.String(length=300), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_total", sa.Float(), nullable=False),
        sa.Column("materials_total", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("cis_deducted_total", sa.Float(), nullable=False),
        sa.Column("net_paid_total", sa.Float(), nullable=False),
        sa.Column("evidence_status", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("matched_bank_transaction_ids", sa.JSON(), nullable=True),
        sa.Column("attestation_json", sa.JSON(), nullable=True),
        sa.Column(
            "report_status",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cis_records_user_id", "cis_records", ["user_id"], unique=False)

    op.create_table(
        "cis_review_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("suspected_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("cis_record_id", sa.Uuid(), nullable=True),
        sa.Column("payer_label", sa.String(length=300), nullable=True),
        sa.Column("suspect_reason", sa.String(length=500), nullable=True),
        sa.Column("next_reminder_at", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cis_review_tasks_user_id", "cis_review_tasks", ["user_id"], unique=False)
    op.create_index(
        "ix_cis_review_tasks_user_status",
        "cis_review_tasks",
        ["user_id", "status"],
        unique=False,
    )

    op.create_table(
        "accountant_delegations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_user_id", sa.String(), nullable=False),
        sa.Column("accountant_user_id", sa.String(), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column(
            "can_submit_hmrc",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_accountant_delegations_client",
        "accountant_delegations",
        ["client_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_accountant_delegations_client", table_name="accountant_delegations")
    op.drop_table("accountant_delegations")
    op.drop_index("ix_cis_review_tasks_user_status", table_name="cis_review_tasks")
    op.drop_index("ix_cis_review_tasks_user_id", table_name="cis_review_tasks")
    op.drop_table("cis_review_tasks")
    op.drop_index("ix_cis_records_user_id", table_name="cis_records")
    op.drop_table("cis_records")
