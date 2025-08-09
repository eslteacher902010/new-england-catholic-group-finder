from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "831e9b18b52a"
down_revision = "8d1f4b737079"   # <- the parent you showed earlier
branch_labels = None
depends_on = None


def _has_column(bind, table, column):
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def upgrade():
    bind = op.get_bind()

    # Add user_id only if missing
    if not _has_column(bind, "event", "user_id"):
        with op.batch_alter_table("event", schema=None) as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        # best-effort index; ignore if it already exists
        try:
            op.create_index("ix_event_user_id", "event", ["user_id"], unique=False)
        except Exception:
            pass

        # backfill to 1 (only if you have user id=1)
        op.execute("UPDATE event SET user_id = 1 WHERE user_id IS NULL")
    else:
        # ensure index exists (ignore if already present)
        try:
            op.create_index("ix_event_user_id", "event", ["user_id"], unique=False)
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    # drop index if present; ignore if it doesn't exist
    try:
        op.drop_index("ix_event_user_id", table_name="event")
    except Exception:
        pass

    if _has_column(bind, "event", "user_id"):
        with op.batch_alter_table("event", schema=None) as batch_op:
            batch_op.drop_column("user_id")
