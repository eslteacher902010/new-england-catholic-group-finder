"""add user_id to event

Revision ID: 1fcae84badf7
Revises: 1f7306c99575
Create Date: 2025-08-09 12:21:57.088248
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1fcae84badf7"
down_revision = "1f7306c99575"
branch_labels = None
depends_on = None


def upgrade():
    # superseded by 831e9b18b52a (SQLite-safe user_id migration)
    pass


def downgrade():
    pass
