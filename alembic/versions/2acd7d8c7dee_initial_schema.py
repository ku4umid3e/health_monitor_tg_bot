"""initial_schema

Revision ID: 2acd7d8c7dee
Revises: 8ae032cbe019
Create Date: 2025-09-19 11:50:31.318442

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    """Create initial database schema."""
    # Create Users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY,
            First_name VARCHAR(250),
            Last_name VARCHAR(250),
            Username VARCHAR(250),
            TelegramId INTEGER
        );
    """)

    # Create ArmLocation table and seed data
    op.execute("""
        CREATE TABLE IF NOT EXISTS ArmLocation (
            ArmLocationID INTEGER PRIMARY KEY,
            LocationName VARCHAR(100)
        );
    """)
    op.execute("""
        INSERT OR IGNORE INTO ArmLocation (ArmLocationID, LocationName) VALUES
            (1, 'Левая рука'),
            (2, 'Правая рука'),
            (3, 'Левое плечо'),
            (4, 'Правое плечо'),
            (5, 'Не указано');
    """)

    # Create BodyPositions table and seed data
    op.execute("""
        CREATE TABLE IF NOT EXISTS BodyPositions (
            BodyPositionID INTEGER PRIMARY KEY,
            PositionName VARCHAR(100)
        );
    """)
    op.execute("""
        INSERT OR IGNORE INTO BodyPositions (BodyPositionID, PositionName) VALUES
            (1, 'Стоя'),
            (2, 'Сидя'),
            (3, 'Лёжа'),
            (4, 'Полу-лёжа'),
            (5, 'Не указано');
    """)

    # Create Comments table
    op.execute("""
        CREATE TABLE IF NOT EXISTS Comments (
            CommentID INTEGER PRIMARY KEY,
            CommentText TEXT
        );
    """)

    # Create Measurements table
    op.execute("""
        CREATE TABLE IF NOT EXISTS Measurements (
            MeasurementID INTEGER PRIMARY KEY,
            UserID INTEGER,
            ArmLocationID INTEGER,
            BodyPositionID INTEGER,
            CommentID INTEGER,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (ArmLocationID) REFERENCES ArmLocation(ArmLocationID),
            FOREIGN KEY (BodyPositionID) REFERENCES BodyPositions(BodyPositionID),
            FOREIGN KEY (CommentID) REFERENCES Comments(CommentID)
        );
    """)

    # Create MeasureDetails table
    op.execute("""
        CREATE TABLE IF NOT EXISTS MeasureDetails (
            MeasureDetailID INTEGER PRIMARY KEY,
            MeasurementID INTEGER,
            SystolicPressure INTEGER,
            DiastolicPressure INTEGER,
            Pulse INTEGER,
            FOREIGN KEY (MeasurementID) REFERENCES Measurements(MeasurementID)
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
