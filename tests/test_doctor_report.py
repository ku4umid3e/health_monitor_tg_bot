from datetime import datetime, timezone

import pytest


def _row(
    timestamp="2026-08-05 05:15:00",
    *,
    comment="Принял лекарство после завтрака",
):
    return (
        1, timestamp, 120, 80, 70, "Сидя", "Левое плечо",
        comment, "Нормально",
    )


def test_utc_timestamp_is_converted_to_moscow():
    from app.doctor_report import prepare_report_rows, utc_to_moscow

    converted = utc_to_moscow(datetime(2026, 8, 5, 5, 15, tzinfo=timezone.utc))
    prepared = prepare_report_rows([_row()])

    assert converted.strftime("%d.%m.%Y %H:%M %Z") == "05.08.2026 08:15 MSK"
    assert prepared[0].timestamp.hour == 8
    assert prepared[0].comment == "Принял лекарство после завтрака"


def test_render_doctor_report_returns_pdf():
    from app.doctor_report import render_doctor_report

    report = render_doctor_report(
        [_row(), _row("2026-08-05 18:00:00", comment="Не было жалоб")],
        [(1, "Конкор", "2,5 мг", "2026-08-05 10:30:00", "taken", "После еды")],
    )

    assert report.read(4) == b"%PDF"
    assert report.name == "doctor_report_2026-08-05_2026-08-05.pdf"
    report.close()


def test_long_comment_is_split_without_losing_text():
    from app.doctor_report import _table_rows, prepare_report_rows

    comment = " ".join(["важная заметка"] * 80)
    table_rows = _table_rows(prepare_report_rows([_row(comment=comment)]))

    rebuilt = " ".join(row[-1].replace("\n", " ") for row in table_rows)
    assert rebuilt == comment
    assert len(table_rows) > 1


@pytest.mark.asyncio
async def test_doctor_report_handler_sends_document(
    temp_db, dummy_update, dummy_context, mocker,
):
    from app import db, measurement

    user = db.get_user(dummy_update.effective_user)
    measurement_id = db.insert("Measurements", {
        "UserID": user["UserID"],
        "ArmLocationID": 1,
        "BodyPositionID": 2,
        "WellBeingID": 2,
        "CommentID": None,
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    })
    db.insert("MeasureDetails", {
        "MeasurementID": measurement_id,
        "SystolicPressure": 120,
        "DiastolicPressure": 80,
        "Pulse": 70,
    })
    dummy_update.callback_query.data = "doctor_report"

    await measurement.send_doctor_report(dummy_update, dummy_context, db_path=temp_db)

    assert dummy_update.callback_query.message.documents[0].startswith(b"%PDF")
    kwargs = dummy_update.callback_query.message.document_kwargs[0]
    assert kwargs["filename"].endswith(".pdf")
    assert "MSK" in kwargs["caption"]


def test_report_relates_recent_medication_to_measurement():
    from app.doctor_report import (
        _recent_medications,
        prepare_medication_rows,
        prepare_report_rows,
    )

    measurement = prepare_report_rows([_row("2026-08-05 15:00:00")])[0]
    medication = prepare_medication_rows([
        (1, "Конкор", "2,5 мг", "2026-08-05 10:30:00", "taken", None),
    ])

    assert _recent_medications(measurement, medication) == (
        "Конкор 2,5 мг — 4 ч 30 мин назад"
    )


@pytest.mark.asyncio
async def test_doctor_report_handler_reports_empty_period(
    temp_db, dummy_update, dummy_context,
):
    from app import measurement

    dummy_update.callback_query.data = "doctor_report"
    await measurement.send_doctor_report(dummy_update, dummy_context, db_path=temp_db)

    assert dummy_update.callback_query.edited_texts[-1] == (
        "За последние 90 дней измерений нет."
    )
