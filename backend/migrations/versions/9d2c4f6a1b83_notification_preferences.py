"""Add account and sender notification preferences."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9d2c4f6a1b83"
down_revision = "f7b2c31d904e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("volume", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "volume BETWEEN 0 AND 100",
            name="ck_notification_preferences_volume",
        ),
    )
    op.create_table(
        "notification_sender_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "volume_factor",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "volume_factor BETWEEN 0 AND 100",
            name="ck_notification_sender_preferences_volume_factor",
        ),
        sa.CheckConstraint(
            "user_id <> sender_id",
            name="ck_notification_sender_preferences_distinct_users",
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_sender_preferences")
    op.drop_table("notification_preferences")
