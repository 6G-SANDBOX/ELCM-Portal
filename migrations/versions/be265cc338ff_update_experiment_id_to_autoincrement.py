"""update experiment.id to AUTOINCREMENT

Revision ID: be265cc338ff
Revises: 6b1af5767b30
Create Date: 2025-06-17 12:00:31.028478

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be265cc338ff'
down_revision = '6b1af5767b30'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'experiment_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id')),
        sa.Column('name', sa.String(64)),
        sa.Column('type', sa.String(16)),
        sa.Column('automated', sa.Boolean),
        sa.Column('test_cases', sa.String),
        sa.Column('ues', sa.String),
        sa.Column('slice', sa.String(64)),
        sa.Column('application', sa.String(64)),
        sa.Column('exclusive', sa.Boolean),
        sa.Column('parameters', sa.String),
        sa.Column('scenario', sa.String(64)),
        sa.Column('reservation_time', sa.Integer),
        sa.Column('remotePlatform', sa.String(128)),
        sa.Column('remoteDescriptor_id', sa.Integer, sa.ForeignKey('experiment.id')),
        sa.Column('remoteNetworkServices', sa.String),
        sqlite_autoincrement=True
    )

    op.execute('''
        INSERT INTO experiment_new (
            id, user_id, name, type, automated, test_cases, ues, slice,
            application, exclusive, parameters, scenario, reservation_time,
            remotePlatform, remoteDescriptor_id, remoteNetworkServices
        )
        SELECT
            id, user_id, name, type, automated, test_cases, ues, slice,
            application, exclusive, parameters, scenario, reservation_time,
            remotePlatform, remoteDescriptor_id, remoteNetworkServices
        FROM experiment
    ''')

    op.drop_table('experiment')
    op.rename_table('experiment_new', 'experiment')



def downgrade():
    pass
