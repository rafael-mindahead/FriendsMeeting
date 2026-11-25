
"""Create friend requests table.

Revision ID: c8a12f7e0b5d
Revises: b9237a11f0a2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c8a12f7e0b5d"
down_revision = "b9237a11f0a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "friend_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "receiver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "sender_id <> receiver_id",
            name="ck_friend_requests_distinct_users",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_friend_requests_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "uq_friend_requests_pair",
        "friend_requests",
        [
            sa.text("LEAST(sender_id, receiver_id)"),
            sa.text("GREATEST(sender_id, receiver_id)"),
        ],
        unique=True,
    )

    op.create_index(
        "ix_friend_requests_receiver_status",
        "friend_requests",
        ["receiver_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_friend_requests_receiver_status",
        table_name="friend_requests",
    )
    op.drop_index(
        "uq_friend_requests_pair",
        table_name="friend_requests",
    )
    op.drop_table("friend_requests")
