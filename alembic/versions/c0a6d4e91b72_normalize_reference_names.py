"""Normalize reference names used by Telegram keyboards.

Revision ID: c0a6d4e91b72
Revises: 8ae032cbe019
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c0a6d4e91b72"
down_revision: Union[str, Sequence[str], None] = "8ae032cbe019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalize legacy labels without changing their stable IDs."""
    op.execute(
        "UPDATE ArmLocation SET LocationName = 'Левое плечо' "
        "WHERE ArmLocationID = 3"
    )
    op.execute(
        "UPDATE ArmLocation SET LocationName = 'Правое плечо' "
        "WHERE ArmLocationID = 4"
    )
    op.execute(
        "UPDATE BodyPositions SET PositionName = 'Полу-лёжа' "
        "WHERE BodyPositionID = 4"
    )


def downgrade() -> None:
    """Restore the legacy labels."""
    op.execute(
        "UPDATE ArmLocation SET LocationName = 'Левое плечё' "
        "WHERE ArmLocationID = 3"
    )
    op.execute(
        "UPDATE ArmLocation SET LocationName = 'Правое плечё' "
        "WHERE ArmLocationID = 4"
    )
    op.execute(
        "UPDATE BodyPositions SET PositionName = 'Полу лёжа' "
        "WHERE BodyPositionID = 4"
    )
