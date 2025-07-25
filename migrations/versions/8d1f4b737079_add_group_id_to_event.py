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
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('group_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_event_group_id', 'catholic', ['group_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.drop_constraint('fk_event_group_id', type_='foreignkey')
        batch_op.drop_column('group_id')

    # ### end Alembic commands ###
