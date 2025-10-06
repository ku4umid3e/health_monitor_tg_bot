import pytest


@pytest.mark.asyncio
async def test_last_measurement_no_records(temp_db, dummy_update, dummy_context):
    from app import measurement

    await measurement.last_measurement(dummy_update, dummy_context, temp_db)

    # First reply should state that there are no records
    assert dummy_update.message.texts[0].startswith("Записей ещё нет.")


@pytest.mark.asyncio
async def test_last_measurement_with_record(temp_db, dummy_update, dummy_context):
    from app import db, measurement

    # Seed one record manually
    user = db.get_user(dummy_update.effective_user)
    comment_id = db.insert('Comments', {'CommentText': 'К'})
    mid = db.insert('Measurements', {
        'UserID': user['UserID'],
        'ArmLocationID': 1,
        'BodyPositionID': 2,
        'WellBeingID': 2,
        'CommentID': comment_id,
    })
    db.insert('MeasureDetails', {
        'MeasurementID': mid,
        'SystolicPressure': 110,
        'DiastolicPressure': 70,
        'Pulse': 65,
    })

    await measurement.last_measurement(dummy_update, dummy_context, temp_db)

    # Now message is edited via inline callback flow
    text = "\n".join(dummy_update.callback_query.edited_texts)
    assert "Последнее измерение:" in text
    assert "АД: 110/70, Пульс: 65" in text
    assert "Самочувствие: Нормально" in text
