"""Database-backed lookup helpers for measurement reference values."""

from __future__ import annotations

import db


DEFAULT_BODY_POSITION_ID = 5
DEFAULT_ARM_LOCATION_ID = 5
DEFAULT_WELL_BEING_ID = 2


def _lookup_id(
    table: str,
    id_column: str,
    name_column: str,
    name: str | None,
    default: int,
    database_path: str | None = None,
) -> int:
    if not name:
        return default
    with db.UseDB(database_path or db.db_name) as cursor:
        cursor.execute(
            f"SELECT {id_column} FROM {table} WHERE {name_column} = ?",
            (name,),
        )
        row = cursor.fetchone()
    return row[0] if row else default


def _lookup_name(
    table: str,
    id_column: str,
    name_column: str,
    value_id: int | None,
    database_path: str | None = None,
) -> str | None:
    if value_id is None:
        return None
    with db.UseDB(database_path or db.db_name) as cursor:
        cursor.execute(
            f"SELECT {name_column} FROM {table} WHERE {id_column} = ?",
            (value_id,),
        )
        row = cursor.fetchone()
    return row[0] if row else None


def get_body_position_id(name: str | None, database_path: str | None = None) -> int:
    return _lookup_id(
        "BodyPositions", "BodyPositionID", "PositionName", name,
        DEFAULT_BODY_POSITION_ID, database_path,
    )


def get_arm_location_id(name: str | None, database_path: str | None = None) -> int:
    return _lookup_id(
        "ArmLocation", "ArmLocationID", "LocationName", name,
        DEFAULT_ARM_LOCATION_ID, database_path,
    )


def get_well_being_id(name: str | None, database_path: str | None = None) -> int:
    return _lookup_id(
        "WellBeing", "WellBeingID", "Name", name,
        DEFAULT_WELL_BEING_ID, database_path,
    )


def get_body_position_name(value_id: int | None, database_path: str | None = None) -> str | None:
    return _lookup_name(
        "BodyPositions", "BodyPositionID", "PositionName", value_id, database_path,
    )


def get_arm_location_name(value_id: int | None, database_path: str | None = None) -> str | None:
    return _lookup_name(
        "ArmLocation", "ArmLocationID", "LocationName", value_id, database_path,
    )


def get_well_being_name(value_id: int | None, database_path: str | None = None) -> str | None:
    return _lookup_name(
        "WellBeing", "WellBeingID", "Name", value_id, database_path,
    )
