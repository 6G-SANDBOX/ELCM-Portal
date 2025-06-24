"""Recreate user and action tables with AUTOINCREMENT"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6b1af5767b30'
down_revision = '3499ae5b9a77'
branch_labels = None
depends_on = None

def upgrade():
    # Recreate 'user' table with AUTOINCREMENT
    op.create_table(
        'user_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(64)),
        sa.Column('email', sa.String(120)),
        sa.Column('password_hash', sa.String(128)),
        sa.Column('organization', sa.String(32)),
        sa.Column('token', sa.String(512)),
        sa.Column('tokenTimestamp', sa.DateTime),
        sa.Column('is_approved', sa.Boolean),
        sa.Column('is_admin', sa.Boolean),
        sqlite_autoincrement=True
    )

    op.execute('''
        INSERT INTO user_new (id, username, email, password_hash, organization, token, tokenTimestamp, is_approved, is_admin)
        SELECT id, username, email, password_hash, organization, token, tokenTimestamp, is_approved, is_admin FROM user
    ''')

    op.drop_table('user')
    op.rename_table('user_new', 'user')

    op.create_index('ix_user_email', 'user', ['email'], unique=True)
    op.create_index('ix_user_username', 'user', ['username'], unique=True)

    # Recreate 'action' table with AUTOINCREMENT
    op.create_table(
        'action_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('timestamp', sa.DateTime),
        sa.Column('message', sa.String(256)),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id')),
        sqlite_autoincrement=True
    )

    op.execute('''
        INSERT INTO action_new (id, timestamp, message, user_id)
        SELECT id, timestamp, message, user_id FROM action
    ''')

    op.drop_table('action')
    op.rename_table('action_new', 'action')

def downgrade():
    pass
