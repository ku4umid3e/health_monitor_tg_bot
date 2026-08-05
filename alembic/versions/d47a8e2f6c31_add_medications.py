"""Add medication catalogue and intake events.

Revision ID: d47a8e2f6c31
Revises: c0a6d4e91b72
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d47a8e2f6c31"
down_revision: Union[str, Sequence[str], None] = "c0a6d4e91b72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user medications and immutable intake history."""
    op.execute("""
        CREATE TABLE Medications (
            MedicationID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER NOT NULL,
            Name TEXT NOT NULL,
            DefaultDose TEXT,
            ScheduleType TEXT NOT NULL DEFAULT 'as_needed'
                CHECK (ScheduleType IN ('daily', 'as_needed')),
            IsQuickAccess INTEGER NOT NULL DEFAULT 1 CHECK (IsQuickAccess IN (0, 1)),
            IsActive INTEGER NOT NULL DEFAULT 1 CHECK (IsActive IN (0, 1)),
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_active_medication_name "
        "ON Medications(UserID, Name) WHERE IsActive = 1"
    )
    op.execute("""
        CREATE TABLE MedicationIntakes (
            IntakeID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER NOT NULL,
            MedicationID INTEGER,
            MedicationNameSnapshot TEXT NOT NULL,
            Dose TEXT,
            TakenAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            Status TEXT NOT NULL DEFAULT 'taken'
                CHECK (Status IN ('taken', 'skipped', 'cancelled')),
            Comment TEXT,
            CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (MedicationID) REFERENCES Medications(MedicationID)
        )
    """)
    op.execute(
        "CREATE INDEX ix_medication_intakes_user_taken_at "
        "ON MedicationIntakes(UserID, TakenAt)"
    )


def downgrade() -> None:
    """Remove medication intake storage."""
    op.execute("DROP TABLE IF EXISTS MedicationIntakes")
    op.execute("DROP TABLE IF EXISTS Medications")
