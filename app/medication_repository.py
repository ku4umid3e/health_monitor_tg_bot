"""SQLite operations for medications and medication-intake events."""

from __future__ import annotations

from datetime import datetime, timezone

import db


class MedicationRepository:
    """Persist user medication settings and intake history."""

    def list_active(self, user_id: int, database_path: str | None = None):
        with db.UseDB(database_path or db.db_name) as cursor:
            cursor.execute(
                "SELECT MedicationID, Name, DefaultDose, ScheduleType, IsQuickAccess "
                "FROM Medications WHERE UserID = ? AND IsActive = 1 "
                "ORDER BY Name COLLATE NOCASE",
                (user_id,),
            )
            return cursor.fetchall()

    def get_owned(self, user_id: int, medication_id: int, database_path: str | None = None):
        with db.UseDB(database_path or db.db_name) as cursor:
            cursor.execute(
                "SELECT MedicationID, Name, DefaultDose, ScheduleType, IsQuickAccess "
                "FROM Medications WHERE UserID = ? AND MedicationID = ? AND IsActive = 1",
                (user_id, medication_id),
            )
            return cursor.fetchone()

    def add_medication(
        self,
        user_id: int,
        *,
        name: str,
        default_dose: str | None,
        schedule_type: str = "as_needed",
        is_quick_access: bool = True,
        database_path: str | None = None,
    ) -> int:
        with db.UnitOfWork(database_path or db.db_name) as uow:
            return uow.insert("Medications", {
                "UserID": user_id,
                "Name": name.strip(),
                "DefaultDose": default_dose.strip() if default_dose else None,
                "ScheduleType": schedule_type,
                "IsQuickAccess": int(is_quick_access),
            })

    def set_quick_access(
        self, user_id: int, medication_id: int, enabled: bool,
        database_path: str | None = None,
    ) -> bool:
        with db.UnitOfWork(database_path or db.db_name) as uow:
            uow.cursor.execute(
                "UPDATE Medications SET IsQuickAccess = ? "
                "WHERE MedicationID = ? AND UserID = ? AND IsActive = 1",
                (int(enabled), medication_id, user_id),
            )
            return uow.cursor.rowcount == 1

    def archive(
        self, user_id: int, medication_id: int, database_path: str | None = None,
    ) -> bool:
        with db.UnitOfWork(database_path or db.db_name) as uow:
            uow.cursor.execute(
                "UPDATE Medications SET IsActive = 0, IsQuickAccess = 0 "
                "WHERE MedicationID = ? AND UserID = ?",
                (medication_id, user_id),
            )
            return uow.cursor.rowcount == 1

    def record_intake(
        self,
        user_id: int,
        *,
        medication_name: str,
        dose: str | None,
        medication_id: int | None = None,
        taken_at: datetime | None = None,
        comment: str | None = None,
        database_path: str | None = None,
    ) -> int:
        timestamp = taken_at or datetime.now(timezone.utc)
        timestamp_utc = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        with db.UnitOfWork(database_path or db.db_name) as uow:
            return uow.insert("MedicationIntakes", {
                "UserID": user_id,
                "MedicationID": medication_id,
                "MedicationNameSnapshot": medication_name.strip(),
                "Dose": dose.strip() if dose else None,
                "TakenAt": timestamp_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "Comment": comment.strip() if comment else None,
            })

    def get_owned_intake(self, user_id: int, intake_id: int, database_path: str | None = None):
        with db.UseDB(database_path or db.db_name) as cursor:
            cursor.execute(
                "SELECT IntakeID, MedicationID, MedicationNameSnapshot, Dose, TakenAt, Status, Comment "
                "FROM MedicationIntakes WHERE IntakeID = ? AND UserID = ?",
                (intake_id, user_id),
            )
            return cursor.fetchone()

    def update_intake(
        self,
        user_id: int,
        intake_id: int,
        *,
        taken_at: datetime | None = None,
        comment: str | None = None,
        status: str | None = None,
        medication_id: int | None = None,
        database_path: str | None = None,
    ) -> bool:
        values: dict[str, object] = {}
        if taken_at is not None:
            values["TakenAt"] = taken_at.astimezone(timezone.utc).replace(
                tzinfo=None
            ).strftime("%Y-%m-%d %H:%M:%S")
        if comment is not None:
            values["Comment"] = comment.strip() or None
        if status is not None:
            values["Status"] = status
        if medication_id is not None:
            values["MedicationID"] = medication_id
        if not values:
            return False
        set_clause = ", ".join(f"{field} = ?" for field in values)
        with db.UnitOfWork(database_path or db.db_name) as uow:
            uow.cursor.execute(
                f"UPDATE MedicationIntakes SET {set_clause} WHERE IntakeID = ? AND UserID = ?",
                (*values.values(), intake_id, user_id),
            )
            return uow.cursor.rowcount == 1

    def list_since_days(
        self, user_id: int, *, days: int = 90, database_path: str | None = None,
    ):
        with db.UseDB(database_path or db.db_name) as cursor:
            cursor.execute(
                "SELECT IntakeID, MedicationNameSnapshot, Dose, TakenAt, Status, Comment "
                "FROM MedicationIntakes WHERE UserID = ? AND Status != 'cancelled' "
                "AND TakenAt >= datetime('now', ?) ORDER BY TakenAt",
                (user_id, f"-{days} day"),
            )
            return cursor.fetchall()
