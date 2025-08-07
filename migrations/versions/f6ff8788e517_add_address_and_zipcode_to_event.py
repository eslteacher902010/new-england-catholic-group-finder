"""Add address and zipcode to Event

Revision ID: f6ff8788e517
Revises: 6b60db82a628
Create Date: 2025-08-04 12:02:17.213958
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f6ff8788e517'
down_revision = '6b60db82a628'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event', sa.Column('address', sa.String(length=250), nullable=True))
    op.add_column('event', sa.Column('zip_code', sa.String(length=10), nullable=True))


def downgrade():
    # op.drop_column('event', 'zipcode')
    # op.drop_column('event', 'address')
    pass



    # ### end Alembic commands #
    # ### end Alembic commands ###
