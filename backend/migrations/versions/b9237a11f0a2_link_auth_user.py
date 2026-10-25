"""Associate FriendsMeeting profiles with external auth identities.

Revision ID: b9237a11f0a2
Revises: 068d1b247387
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b9237a11f0a2"
down_revision: Union[str, Sequence[str], None] = "068d1b247387"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Preserve existing local accounts; new accounts use authService identities.
    op.add_column("users", sa.Column("auth_user_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_auth_user_id", "users", ["auth_user_id"], unique=True)
    # No password is stored for externally authenticated profiles.
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(length=255),
        nullable=True, existing_nullable=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    missing_passwords = connection.execute(
        sa.text("SELECT count(*) FROM users WHERE password_hash IS NULL")
    ).scalar_one()
    if missing_passwords:
        raise RuntimeError(
            "Cannot downgrade without losing external-auth profiles; "
            "migrate them first"
        )
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(length=255),
        nullable=False, existing_nullable=True,
    )
    op.drop_index("ix_users_auth_user_id", table_name="users")
    op.drop_column("users", "auth_user_id")
