import pytest


@pytest.mark.asyncio
async def test_add_measurement_success(temp_db, dummy_update, dummy_context):
    from app import measurement
    # Simulate collected data
    dummy_context.user_data["measurements"] = {
        "pressure": ["120", "80"],
        "pulse": ["70"],
        "body_position": "Сидя",
        "arm_location": "Левая рука",
        "well_being": "Нормально",
        "comment": "Тестовая запись",
    }

    await measurement.add_measurement(dummy_update, dummy_context)

    # Verify DB wrote records
    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT COUNT(*) FROM Measurements")
        meas_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM MeasureDetails")
        det_cnt = cursor.fetchone()[0]
    assert meas_cnt == 1
    assert det_cnt == 1


@pytest.mark.asyncio
async def test_add_measurement_invalid_input_no_write(temp_db, dummy_update, dummy_context):
    from app import measurement
    # Broken pressure
    dummy_context.user_data["measurements"] = {
        "pressure": ["120"],
        "pulse": ["70"],
        "body_position": "Сидя",
        "arm_location": "Левая рука",
        "well_being": "Нормально",
        "comment": "",
    }

    await measurement.add_measurement(dummy_update, dummy_context)

    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT COUNT(*) FROM Measurements")
        meas_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM MeasureDetails")
        det_cnt = cursor.fetchone()[0]
    assert meas_cnt == 0
    assert det_cnt == 0


@pytest.mark.asyncio
async def test_full_measurement_dialog_flow(temp_db, dummy_update, dummy_context, mocker):
    from app import measurement
    from app import bot_messages
    from telegram.ext import ConversationHandler

    # Mock reply_text to capture bot's responses
    mocker.patch.object(dummy_update.message, 'reply_text', autospec=True)

    # 1. Start the conversation
    dummy_update.message.text = "Записать результат измерения"
    result = await measurement.start_add_measurement(dummy_update, dummy_context)
    assert result == "blood_pressure"
    dummy_update.message.reply_text.assert_called_with(
        bot_messages.INPUT_PRESSURE,
        reply_markup=mocker.ANY  # ReplyKeyboardRemove is sent here
    )

    # 2. Enter valid blood pressure
    dummy_update.message.text = "120/80"
    result = await measurement.blood_pressure(dummy_update, dummy_context)
    assert result == "pulse"
    assert dummy_context.user_data['measurements']['pressure'] == ['120', '80']
    dummy_update.message.reply_text.assert_called_with(
        "Ок, так и запишим 120 на 80,\nА какой пульс?"
    )

    # 3. Enter valid pulse
    dummy_update.message.text = "70"
    result = await measurement.pulse(dummy_update, dummy_context)
    assert result == "body_position"
    assert dummy_context.user_data['measurements']['pulse'] == ['70']
    dummy_update.message.reply_text.assert_called_with(
        "Ок, так и запишим ваш пульс 70.\nВыбери положение при котором происходил замер.",
        reply_markup=mocker.ANY  # BODY_POSITION_KEYBOARD
    )

    # 4. Select body position
    dummy_update.message.text = "Сидя"
    result = await measurement.body_position(dummy_update, dummy_context)
    assert result == "arm_location"
    assert dummy_context.user_data['measurements']['body_position'] == "Сидя"
    dummy_update.message.reply_text.assert_called_with(
        "Выбери положение манжеты на руке.",
        reply_markup=mocker.ANY  # ARM_LOCATION_KEYBOARD
    )

    # 5. Select arm location
    dummy_update.message.text = "Левое плечё"
    result = await measurement.arm_location(dummy_update, dummy_context)
    assert result == "well_being"
    assert dummy_context.user_data['measurements']['arm_location'] == "Левое плечё"
    dummy_update.message.reply_text.assert_called_with(
        "Как самочувствие?",
        reply_markup=mocker.ANY  # WELL_BEING_KEYBOARD
    )

    # 6. Select well-being
    dummy_update.message.text = "Нормально"
    result = await measurement.well_being(dummy_update, dummy_context)
    assert result == "comment"
    assert dummy_context.user_data['measurements']['well_being'] == "Нормально"
    dummy_update.message.reply_text.assert_called_with(
        "Любые жалобы или заметки? (можно пропустить)",
        reply_markup=mocker.ANY  # ReplyKeyboardRemove
    )

    # 7. Enter comment and finalize
    dummy_update.message.text = "Немного устал"
    result = await measurement.comment(dummy_update, dummy_context)
    assert result == ConversationHandler.END
    assert dummy_context.user_data['measurements']['comment'] == "Немного устал"
    dummy_update.message.reply_text.assert_called_with(
        'Супер! Я записал измерение:\n'
        'АД: 120/80, Пульс: 70\n'
        'Положение: Сидя, Манжета: Левое плечё\n'
        'Самочувствие: Нормально\n'
        'Комментарий: Немного устал',
        reply_markup=mocker.ANY  # WLCOME_KEYBOARD
    )

    # Verify DB wrote records
    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT COUNT(*) FROM Measurements")
        meas_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM MeasureDetails")
        det_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Comments WHERE CommentText = 'Немного устал'")
        comment_cnt = cursor.fetchone()[0]
    assert meas_cnt == 1
    assert det_cnt == 1
    assert comment_cnt == 1


@pytest.mark.asyncio
async def test_full_measurement_dialog_invalid_pressure(temp_db, dummy_update, dummy_context, mocker):
    from app import measurement
    from app import bot_messages

    mocker.patch.object(dummy_update.message, 'reply_text', autospec=True)

    # 1. Start the conversation
    dummy_update.message.text = "Записать результат измерения"
    result = await measurement.start_add_measurement(dummy_update, dummy_context)
    assert result == "blood_pressure"
    dummy_update.message.reply_text.assert_called_with(
        bot_messages.INPUT_PRESSURE,
        reply_markup=mocker.ANY
    )

    # 2. Enter invalid blood pressure
    dummy_update.message.text = "120"
    result = await measurement.blood_pressure(dummy_update, dummy_context)
    assert result == "blood_pressure"  # Should stay in the same state
    dummy_update.message.reply_text.assert_called_with(bot_messages.WRONG_PRESSURE)

    # Verify no records were written to DB
    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT COUNT(*) FROM Measurements")
        meas_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM MeasureDetails")
        det_cnt = cursor.fetchone()[0]
    assert meas_cnt == 0
    assert det_cnt == 0


@pytest.mark.asyncio
async def test_full_measurement_dialog_invalid_pulse(temp_db, dummy_update, dummy_context, mocker):
    from app import measurement
    from app import bot_messages

    mocker.patch.object(dummy_update.message, 'reply_text', autospec=True)

    # 1. Start the conversation
    dummy_update.message.text = "Записать результат измерения"
    result = await measurement.start_add_measurement(dummy_update, dummy_context)
    assert result == "blood_pressure"

    # 2. Enter valid blood pressure
    dummy_update.message.text = "120/80"
    result = await measurement.blood_pressure(dummy_update, dummy_context)
    assert result == "pulse"

    # 3. Enter invalid pulse
    dummy_update.message.text = "abc"
    result = await measurement.pulse(dummy_update, dummy_context)
    assert result == "pulse"  # Should stay in the same state
    dummy_update.message.reply_text.assert_called_with(bot_messages.WRONG_PULSE)

    # Verify no records were written to DB
    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT COUNT(*) FROM Measurements")
        meas_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM MeasureDetails")
        det_cnt = cursor.fetchone()[0]
    assert meas_cnt == 0
    assert det_cnt == 0
