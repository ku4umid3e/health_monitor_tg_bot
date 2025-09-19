"""add wellbeing

Revision ID: 8ae032cbe019
Revises:
Create Date: 2025-09-18 22:55:18.554563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ae032cbe019'
down_revision: Union[str, Sequence[str], None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS WellBeing (
            WellBeingID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL UNIQUE
        );
    """)
    op.execute("""
        INSERT OR IGNORE INTO WellBeing (Name) VALUES ('Хорошо'), ('Нормально'), ('Плохо');
    """)
    op.execute("""
        ALTER TABLE Measurements ADD COLUMN WellBeingID INTEGER REFERENCES WellBeing(WellBeingID);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE Measurements DROP COLUMN WellBeingID;")
    op.execute("DROP TABLE IF EXISTS WellBeing;")