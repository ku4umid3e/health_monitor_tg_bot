from datetime import datetime, timezone

import pytest


def test_medication_repository_records_snapshot_and_archives(temp_db, dummy_update):
    from app import db
    from app.medication_repository import MedicationRepository

    repository = MedicationRepository()
    user_id = db.get_user(dummy_update.effective_user)["UserID"]
    medication_id = repository.add_medication(
        user_id,
        name="Конкор",
        default_dose="2,5 мг",
        schedule_type="daily",
    )
    intake_id = repository.record_intake(
        user_id,
        medication_id=medication_id,
        medication_name="Конкор",
        dose="2,5 мг",
        taken_at=datetime(2026, 8, 5, 9, 30, tzinfo=timezone.utc),
    )

    intake = repository.get_owned_intake(user_id, intake_id)
    assert intake[2:6] == ("Конкор", "2,5 мг", "2026-08-05 09:30:00", "taken")
    assert repository.archive(user_id, medication_id)
    assert repository.list_active(user_id) == []
    assert repository.get_owned_intake(user_id, intake_id)[2] == "Конкор"


@pytest.mark.asyncio
async def test_quick_intake_is_recorded_in_one_selection(
    temp_db, dummy_update, dummy_context,
):
    from app import db, medication

    user_id = db.get_user(dummy_update.effective_user)["UserID"]
    medication_id = medication.repo.add_medication(
        user_id, name="Конкор", default_dose="2,5 мг", schedule_type="daily",
    )

    state = await medication.start_medication_intake(dummy_update, dummy_context)
    assert state == "intake_choice"
    dummy_update.callback_query.data = f"med_take:{medication_id}"
    result = await medication.intake_choice(dummy_update, dummy_context)

    from telegram.ext import ConversationHandler
    assert result == ConversationHandler.END
    with db.UseDB(db.db_name) as cursor:
        cursor.execute(
            "SELECT MedicationNameSnapshot, Dose, Status FROM MedicationIntakes"
        )
        assert cursor.fetchone() == ("Конкор", "2,5 мг", "taken")
    assert "Конкор 2,5 мг" in dummy_update.callback_query.edited_texts[-1]


@pytest.mark.asyncio
async def test_arbitrary_intake_can_be_saved_as_quick_medication(
    temp_db, dummy_update, dummy_context,
):
    from app import db, medication

    dummy_context.user_data["medication_draft"] = {"name": "Нурофен"}
    dummy_update.message.text = "200 мг"
    await medication.arbitrary_dose(dummy_update, dummy_context)

    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT IntakeID FROM MedicationIntakes")
        intake_id = cursor.fetchone()[0]
    dummy_update.callback_query.data = f"med_save:{intake_id}"
    await medication.save_one_off(dummy_update, dummy_context)

    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT Name, DefaultDose, IsQuickAccess FROM Medications")
        assert cursor.fetchone() == ("Нурофен", "200 мг", 1)


@pytest.mark.asyncio
async def test_edit_intake_time_uses_moscow_time(
    temp_db, dummy_update, dummy_context,
):
    from app import db, medication

    user_id = db.get_user(dummy_update.effective_user)["UserID"]
    intake_id = medication.repo.record_intake(
        user_id,
        medication_name="Анальгин",
        dose=None,
        taken_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
    )
    dummy_context.user_data["medication_edit_intake"] = intake_id
    dummy_update.message.text = "15:30"

    await medication.edit_time(dummy_update, dummy_context)

    row = medication.repo.get_owned_intake(user_id, intake_id)
    assert row[4] == "2026-08-05 12:30:00"
