from __future__ import annotations

import logging
from typing import Dict

from logging_config import configure_logging
from db import UseDB, db_name


configure_logging()
logger = logging.getLogger(__name__)


# In-memory caches for reference tables
_body_position_name_to_id: Dict[str, int] = {}
_body_position_id_to_name: Dict[int, str] = {}

_arm_location_name_to_id: Dict[str, int] = {}
_arm_location_id_to_name: Dict[int, str] = {}

_well_being_name_to_id: Dict[str, int] = {}
_well_being_id_to_name: Dict[int, str] = {}


# Defaults (should match seeded data)
DEFAULT_BODY_POSITION_ID = 5  # "Не указано"
DEFAULT_ARM_LOCATION_ID = 5   # "Не указано"
DEFAULT_WELL_BEING_ID = 2     # "Нормально"


def _ensure_body_positions_loaded() -> None:
    if _body_position_name_to_id:
        return
    with UseDB(db_name) as cursor:
        cursor.execute("SELECT BodyPositionID, PositionName FROM BodyPositions")
        rows = cursor.fetchall()
    for _id, name in rows:
        _body_position_name_to_id[name] = _id
        _body_position_id_to_name[_id] = name


def _ensure_arm_locations_loaded() -> None:
    if _arm_location_name_to_id:
        return
    with UseDB(db_name) as cursor:
        cursor.execute("SELECT ArmLocationID, LocationName FROM ArmLocation")
        rows = cursor.fetchall()
    for _id, name in rows:
        _arm_location_name_to_id[name] = _id
        _arm_location_id_to_name[_id] = name


def _ensure_well_being_loaded() -> None:
    if _well_being_name_to_id:
        return
    with UseDB(db_name) as cursor:
        cursor.execute("SELECT WellBeingID, Name FROM WellBeing")
        rows = cursor.fetchall()
    for _id, name in rows:
        _well_being_name_to_id[name] = _id
        _well_being_id_to_name[_id] = name


def get_body_position_id(name: str | None) -> int:
    _ensure_body_positions_loaded()
    if not name:
        return DEFAULT_BODY_POSITION_ID
    return _body_position_name_to_id.get(name, DEFAULT_BODY_POSITION_ID)


def get_arm_location_id(name: str | None) -> int:
    _ensure_arm_locations_loaded()
    if not name:
        return DEFAULT_ARM_LOCATION_ID
    return _arm_location_name_to_id.get(name, DEFAULT_ARM_LOCATION_ID)


def get_well_being_id(name: str | None) -> int:
    _ensure_well_being_loaded()
    if not name:
        return DEFAULT_WELL_BEING_ID
    return _well_being_name_to_id.get(name, DEFAULT_WELL_BEING_ID)


def get_body_position_name(_id: int | None) -> str | None:
    if _id is None:
        return None
    _ensure_body_positions_loaded()
    return _body_position_id_to_name.get(_id)


def get_arm_location_name(_id: int | None) -> str | None:
    if _id is None:
        return None
    _ensure_arm_locations_loaded()
    return _arm_location_id_to_name.get(_id)


def get_well_being_name(_id: int | None) -> str | None:
    if _id is None:
        return None
    _ensure_well_being_loaded()
    return _well_being_id_to_name.get(_id)

