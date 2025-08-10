"""edit-event + set-null group_id

Revision ID: 2cf2208f3076
Revises: 14d351de61fb
Create Date: 2025-08-10 17:11:56.042422
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2cf2208f3076"
down_revision = "14d351de61fb"
branch_labels = None
depends_on = None


def upgrade():
    # event: make group_id nullable + add named FK with ON DELETE SET NULL
    with op.batch_alter_table("event", recreate="always") as batch_op:
        batch_op.alter_column("group_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key(
            "fk_event_group_id",
            "catholic",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_event_date_time", ["date_time"])
        batch_op.create_index("ix_event_status", ["status"])

    # followers: explicit, named FKs with CASCADE
    with op.batch_alter_table("followers", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_followers_user_id", "user", ["user_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            "fk_followers_group_id",
            "catholic",
            ["group_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # signups: explicit, named FKs with CASCADE
    with op.batch_alter_table("signups", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_signups_event_id", "event", ["event_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            "fk_signups_user_id", "user", ["user_id"], ["id"], ondelete="CASCADE"
        )

    # user: add the email index detected by autogen
    with op.batch_alter_table("user") as batch_op:
        batch_op.create_index("ix_user_email", ["email"], unique=False)


def downgrade():
    # user: drop email index (simple revert)
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_index("ix_user_email")

    # signups: recreate without explicit FKs (simple revert)
    with op.batch_alter_table("signups", recreate="always") as batch_op:
        pass

    # followers: recreate without explicit FKs
    with op.batch_alter_table("followers", recreate="always") as batch_op:
        pass

    # event: make group_id NOT NULL again (previous state)
    with op.batch_alter_table("event", recreate="always") as batch_op:
        batch_op.alter_column("group_id", existing_type=sa.Integer(), nullable=False)
