import sqlite3

import pytest
from telegram.ext import ConversationHandler


def _seed_measurement(app_db, user_id, *, comment="До изменения"):
    comment_id = app_db.insert("Comments", {"CommentText": comment})
    measurement_id = app_db.insert("Measurements", {
        "UserID": user_id,
        "ArmLocationID": 1,
        "BodyPositionID": 2,
        "WellBeingID": 2,
        "CommentID": comment_id,
    })
    app_db.insert("MeasureDetails", {
        "MeasurementID": measurement_id,
        "SystolicPressure": 120,
        "DiastolicPressure": 80,
        "Pulse": 70,
    })
    return measurement_id, comment_id


@pytest.mark.asyncio
async def test_editor_reloads_last_measurement(temp_db, dummy_update, dummy_context):
    from app import db, measurement

    user = db.get_user(dummy_update.effective_user)
    measurement_id, _ = _seed_measurement(db, user["UserID"])
    dummy_context.user_data.clear()

    state = await measurement.edit_last_measurement(dummy_update, dummy_context)

    assert state == "edit_choice_field"
    assert dummy_context.user_data["edit_measurement"]["MeasurementID"] == measurement_id
    assert "Изменение последнего измерения" in dummy_update.callback_query.edited_texts[-1]


@pytest.mark.asyncio
async def test_inline_choice_updates_draft(temp_db, dummy_update, dummy_context):
    from app import db, measurement

    user = db.get_user(dummy_update.effective_user)
    _seed_measurement(db, user["UserID"])
    await measurement.edit_last_measurement(dummy_update, dummy_context)
    dummy_update.callback_query.data = "set_body_position:4"

    state = await measurement.edit_menu_click(dummy_update, dummy_context)

    draft = dummy_context.user_data["edit_measurement"]
    assert state == "edit_choice_field"
    assert draft["PositionName"] == "Полу-лёжа"
    assert "body_position" in draft["_dirty_fields"]


@pytest.mark.asyncio
async def test_save_edit_updates_transactionally(temp_db, dummy_update, dummy_context):
    from app import db, measurement

    user = db.get_user(dummy_update.effective_user)
    measurement_id, old_comment_id = _seed_measurement(db, user["UserID"])
    await measurement.edit_last_measurement(dummy_update, dummy_context)
    draft = dummy_context.user_data["edit_measurement"]
    draft.update({"SystolicPressure": 130, "DiastolicPressure": 85, "Comments": "После"})
    draft["_dirty_fields"].update({"pressure", "comment"})

    result = await measurement.save_edit(dummy_update, dummy_context)

    assert result == ConversationHandler.END
    assert "edit_measurement" not in dummy_context.user_data
    with sqlite3.connect(temp_db) as connection:
        details = connection.execute(
            "SELECT SystolicPressure, DiastolicPressure FROM MeasureDetails "
            "WHERE MeasurementID = ?", (measurement_id,),
        ).fetchone()
        comment = connection.execute(
            "SELECT C.CommentText FROM Measurements M "
            "JOIN Comments C ON C.CommentID = M.CommentID "
            "WHERE M.MeasurementID = ?", (measurement_id,),
        ).fetchone()
        old_comment = connection.execute(
            "SELECT 1 FROM Comments WHERE CommentID = ?", (old_comment_id,),
        ).fetchone()
    assert details == (130, 85)
    assert comment == ("После",)
    assert old_comment is None


def test_update_rejects_measurement_owned_by_another_user(temp_db, dummy_update):
    from app import db, measurement

    owner = db.get_user(dummy_update.effective_user)
    measurement_id, _ = _seed_measurement(db, owner["UserID"])
    draft = {
        "MeasurementID": measurement_id,
        "Pulse": 90,
        "_dirty_fields": {"pulse"},
    }

    with pytest.raises(LookupError):
        measurement.update_measurement_in_db(
            draft, user_id=owner["UserID"] + 1000, database_path=temp_db,
        )

    with sqlite3.connect(temp_db) as connection:
        pulse = connection.execute(
            "SELECT Pulse FROM MeasureDetails WHERE MeasurementID = ?",
            (measurement_id,),
        ).fetchone()[0]
    assert pulse == 70


def test_reference_names_are_normalized_by_migration(temp_db):
    with sqlite3.connect(temp_db) as connection:
        body_position = connection.execute(
            "SELECT PositionName FROM BodyPositions WHERE BodyPositionID = 4"
        ).fetchone()[0]
        arm_location = connection.execute(
            "SELECT LocationName FROM ArmLocation WHERE ArmLocationID = 3"
        ).fetchone()[0]

    assert body_position == "Полу-лёжа"
    assert arm_location == "Левое плечо"
