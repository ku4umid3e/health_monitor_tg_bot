from __future__ import annotations

from typing import Optional, Tuple

from logging_config import configure_logging
import logging

import db
from db import UnitOfWork


configure_logging()
logger = logging.getLogger(__name__)


class MeasurementRepository:
    """Repository for measurement-related DB operations.

    Keeps SQL localized and allows grouping multi-table changes via UnitOfWork.
    """

    def insert_with_details(
        self,
        uow: UnitOfWork,
        *,
        user_id: int,
        systolic: int,
        diastolic: int,
        pulse: int,
        body_position_id: Optional[int],
        arm_location_id: Optional[int],
        well_being_id: Optional[int],
        comment_text: Optional[str],
    ) -> Tuple[int, int, Optional[int]]:
        comment_id = None
        if comment_text and comment_text.strip():
            comment_id = uow.insert('Comments', {'CommentText': comment_text.strip()})

        measurement_id = uow.insert('Measurements', {
            'UserID': user_id,
            'ArmLocationID': arm_location_id,
            'BodyPositionID': body_position_id,
            'WellBeingID': well_being_id,
            'CommentID': comment_id,
        })

        details_id = uow.insert('MeasureDetails', {
            'MeasurementID': measurement_id,
            'SystolicPressure': systolic,
            'DiastolicPressure': diastolic,
            'Pulse': pulse,
        })

        logger.info("Inserted measurement %s with details %s", measurement_id, details_id)
        return measurement_id, details_id, comment_id

    def get_last_by_user(self, user_id: int, database_path: str | None = None):
        query = (
            "SELECT M.MeasurementID, M.Timestamp, MD.SystolicPressure, MD.DiastolicPressure, MD.Pulse, "
            "BP.PositionName, AL.LocationName, C.CommentText, WB.Name "
            "FROM Measurements M "
            "JOIN MeasureDetails MD ON MD.MeasurementID = M.MeasurementID "
            "LEFT JOIN BodyPositions BP ON BP.BodyPositionID = M.BodyPositionID "
            "LEFT JOIN ArmLocation AL ON AL.ArmLocationID = M.ArmLocationID "
            "LEFT JOIN Comments C ON C.CommentID = M.CommentID "
            "LEFT JOIN WellBeing WB ON WB.WellBeingID = M.WellBeingID "
            "WHERE M.UserID = ? "
            "ORDER BY M.Timestamp DESC LIMIT 1"
        )
        with db.UseDB(database_path or db.db_name) as cursor:
            cursor.execute(query, (user_id,))
            return cursor.fetchone()

    def list_since_days(
        self,
        user_id: int,
        *,
        days: int = 3,
        database_path: str | None = None,
    ):
        query = (
            "SELECT M.MeasurementID, M.Timestamp, MD.SystolicPressure, MD.DiastolicPressure, MD.Pulse, "
            "BP.PositionName, AL.LocationName, C.CommentText, WB.Name "
            "FROM Measurements M "
            "JOIN MeasureDetails MD ON MD.MeasurementID = M.MeasurementID "
            "LEFT JOIN BodyPositions BP ON BP.BodyPositionID = M.BodyPositionID "
            "LEFT JOIN ArmLocation AL ON AL.ArmLocationID = M.ArmLocationID "
            "LEFT JOIN Comments C ON C.CommentID = M.CommentID "
            "LEFT JOIN WellBeing WB ON WB.WellBeingID = M.WellBeingID "
            "WHERE M.UserID = ? AND M.Timestamp >= datetime(\"now\", ?) "
            "ORDER BY M.Timestamp DESC"
        )
        with db.UseDB(database_path or db.db_name) as cursor:
            cursor.execute(query, (user_id, f"-{days} day"))
            return cursor.fetchall()

    def update_measurement(
        self,
        uow: UnitOfWork,
        *,
        measurement_id: int,
        user_id: int,
        systolic: Optional[int] = None,
        diastolic: Optional[int] = None,
        pulse: Optional[int] = None,
        body_position_id: Optional[int] = None,
        arm_location_id: Optional[int] = None,
        well_being_id: Optional[int] = None,
        comment_text: Optional[str] = None,
        remove_comment: bool = False,
    ) -> None:
        uow.cursor.execute(
            "SELECT CommentID FROM Measurements "
            "WHERE MeasurementID = ? AND UserID = ?",
            (measurement_id, user_id),
        )
        owner_row = uow.cursor.fetchone()
        if owner_row is None:
            raise LookupError("Measurement does not belong to the current user")
        old_comment_id = owner_row[0]

        details_update = {}
        if systolic is not None:
            details_update['SystolicPressure'] = systolic
        if diastolic is not None:
            details_update['DiastolicPressure'] = diastolic
        if pulse is not None:
            details_update['Pulse'] = pulse
        if details_update:
            uow.update('MeasureDetails', measurement_id, details_update, 'MeasurementID')

        measurement_updates = {}
        if body_position_id is not None:
            measurement_updates['BodyPositionID'] = body_position_id
        if arm_location_id is not None:
            measurement_updates['ArmLocationID'] = arm_location_id
        if well_being_id is not None:
            measurement_updates['WellBeingID'] = well_being_id

        if remove_comment:
            measurement_updates['CommentID'] = None
        elif comment_text is not None:
            if comment_text.strip():
                comment_id = uow.insert('Comments', {'CommentText': comment_text.strip()})
                measurement_updates['CommentID'] = comment_id
            else:
                measurement_updates['CommentID'] = None

        if measurement_updates:
            uow.update('Measurements', measurement_id, measurement_updates, 'MeasurementID')

        if old_comment_id and (remove_comment or comment_text is not None):
            uow.delete('Comments', old_comment_id, 'CommentID')

        logger.info("Updated measurement %s", measurement_id)
