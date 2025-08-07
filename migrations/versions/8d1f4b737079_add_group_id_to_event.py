"""Add group_id to Event

Revision ID: 8d1f4b737079
Revises: 24affba81f11
Create Date: 2025-07-15 11:49:24.844338

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d1f4b737079'
down_revision = '24affba81f11'
branch_labels = None
depends_on = None



def upgrade():
    with op.batch_alter_table('event') as batch_op:
        batch_op.add_column(sa.Column('zip_code', sa.String(length=10), nullable=True))

    # Copy data from 'zipcode' to 'zip_code'
    op.execute('UPDATE event SET zip_code = zipcode')

    with op.batch_alter_table('event') as batch_op:
        batch_op.drop_column('zipcode')


def downgrade():
    with op.batch_alter_table('event') as batch_op:
        batch_op.add_column(sa.Column('zipcode', sa.String(length=10), nullable=True))

    op.execute('UPDATE event SET zipcode = zip_code')

    with op.batch_alter_table('event') as batch_op:
        batch_op.drop_column('zip_code')


    # ### end Alembic commands ###
