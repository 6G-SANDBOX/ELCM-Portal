"""Recreate user and action tables with AUTOINCREMENT"""

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '6b1af5767b30'
down_revision = '3499ae5b9a77'
branch_labels = None
depends_on = None

def upgrade():

    op.execute(text('''
        CREATE TABLE user_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(64),
            email VARCHAR(120),
            password_hash VARCHAR(128),
            organization VARCHAR(32),
            token VARCHAR(512),
            tokenTimestamp DATETIME,
            is_approved BOOLEAN,
            is_admin BOOLEAN
        )
    '''))

    op.execute(text('''
        INSERT INTO user_new (id, username, email, password_hash, organization, token, tokenTimestamp, is_approved, is_admin)
        SELECT id, username, email, password_hash, organization, token, tokenTimestamp, is_approved, is_admin FROM user
    '''))

    op.execute(text('DROP TABLE user'))
    op.execute(text('ALTER TABLE user_new RENAME TO user'))

    op.execute(text('''
        CREATE TABLE action_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            message VARCHAR(256),
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )
    '''))

    op.execute(text('''
        INSERT INTO action_new (id, timestamp, message, user_id)
        SELECT id, timestamp, message, user_id FROM action
    '''))

    op.execute(text('DROP TABLE action'))
    op.execute(text('ALTER TABLE action_new RENAME TO action'))

def downgrade():
    pass
