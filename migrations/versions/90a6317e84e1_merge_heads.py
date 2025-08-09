"""merge heads

Revision ID: 90a6317e84e1
Revises: 1fcae84badf7, 831e9b18b52a
Create Date: 2025-08-09 12:33:30.871964

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90a6317e84e1'
down_revision = ('1fcae84badf7', '831e9b18b52a')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
