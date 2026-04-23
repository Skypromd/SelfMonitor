"""user_businesses + transactions.business_id

Revision ID: b7e1c2000004
Revises: a9e4f2000003
Create Date: 2026-04-23 10:00:00.000000

"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e1c2000004"
down_revision: Union[str, None] = "a9e4f2000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_BUSINESS_NS = uuid.UUID("018f0d8e-7f3a-7b3d-9c2a-1e2f3a4b6d7d")


def upgrade() -> None:
    op.create_table(
        "user_businesses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_businesses_user_id", "user_businesses", ["user_id"], unique=False)
    op.add_column("transactions", sa.Column("business_id", sa.Uuid(), nullable=True))
    op.create_index("ix_transactions_business_id", "transactions", ["business_id"], unique=False)
    op.create_foreign_key(
        "fk_transactions_business_id",
        "transactions",
        "user_businesses",
        ["business_id"],
        ["id"],
    )

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT DISTINCT user_id FROM transactions")).fetchall()
    for (uid,) in rows:
        if not uid:
            continue
        bid = str(uuid.uuid5(_DEFAULT_BUSINESS_NS, str(uid)))
        bind.execute(
            sa.text(
                "INSERT INTO user_businesses (id, user_id, display_name) "
                "VALUES (CAST(:bid AS uuid), :uid, :dn)"
            ),
            {"bid": bid, "uid": uid, "dn": "Primary"},
        )
    bind.execute(
        sa.text(
            """
            UPDATE transactions AS t
            SET business_id = ub.id
            FROM user_businesses AS ub
            WHERE ub.user_id = t.user_id AND ub.display_name = 'Primary'
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_business_id", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_business_id", table_name="transactions")
    op.drop_column("transactions", "business_id")
    op.drop_index("ix_user_businesses_user_id", table_name="user_businesses")
    op.drop_table("user_businesses")
