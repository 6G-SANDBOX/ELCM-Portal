"""Remove network_services

Revision ID: 0717943aa0a5
Revises: 56345866eed9
Create Date: 2024-10-07 15:46:40.777919

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0717943aa0a5'
down_revision = '56345866eed9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('vnfd_package')
    op.drop_table('network_service')
    op.drop_table('experiments_ns')
    with op.batch_alter_table('experiment', schema=None) as batch_op:
        batch_op.alter_column('type',
               existing_type=sa.VARCHAR(length=32),
               type_=sa.String(length=16),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('experiment', schema=None) as batch_op:
        batch_op.alter_column('type',
               existing_type=sa.String(length=16),
               type_=sa.VARCHAR(length=32),
               existing_nullable=True)

    op.create_table('experiments_ns',
    sa.Column('experiment_id', sa.INTEGER(), nullable=True),
    sa.Column('ns_id', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['experiment_id'], ['experiment.id'], ),
    sa.ForeignKeyConstraint(['ns_id'], ['network_service.id'], )
    )
    op.create_table('network_service',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=True),
    sa.Column('name', sa.VARCHAR(length=64), nullable=True),
    sa.Column('description', sa.VARCHAR(length=256), nullable=True),
    sa.Column('is_public', sa.BOOLEAN(), nullable=True),
    sa.Column('vim_image', sa.VARCHAR(length=256), nullable=True),
    sa.Column('vim_location', sa.VARCHAR(length=64), nullable=True),
    sa.Column('vim_id', sa.VARCHAR(length=256), nullable=True),
    sa.Column('nsd_file', sa.VARCHAR(length=256), nullable=True),
    sa.Column('nsd_id', sa.VARCHAR(length=256), nullable=True),
    sa.Column('vim_name', sa.VARCHAR(length=64), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('vnfd_package',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('service_id', sa.INTEGER(), nullable=True),
    sa.Column('vnfd_file', sa.VARCHAR(length=256), nullable=True),
    sa.Column('vnfd_id', sa.VARCHAR(length=256), nullable=True),
    sa.ForeignKeyConstraint(['service_id'], ['network_service.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
