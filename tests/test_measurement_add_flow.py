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
