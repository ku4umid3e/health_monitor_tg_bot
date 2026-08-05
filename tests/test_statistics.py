from datetime import datetime
from io import BytesIO

import pytest


def _row(timestamp, systolic, diastolic, pulse):
    return (1, timestamp, systolic, diastolic, pulse, None, None, None, None)


def test_week_report_keeps_every_measurement():
    from app.health_statistics import build_statistics_report

    rows = [
        _row("2026-07-20 20:00:00", 130, 85, 75),
        _row("2026-07-20 08:00:00", 120, 80, 65),
    ]

    report = build_statistics_report(rows, days=7, daily_aggregation=False)

    assert report.count == 2
    assert [point.systolic for point in report.chart_points] == [120, 130]
    assert report.median_systolic == 125
    assert report.median_pulse == 70


def test_month_report_uses_daily_median_and_range():
    from app.health_statistics import build_statistics_report

    rows = [
        _row("2026-07-20 08:00:00", 110, 70, 60),
        _row("2026-07-20 20:00:00", 130, 90, 80),
        _row("2026-07-21 08:00:00", 125, 82, 72),
    ]

    report = build_statistics_report(rows, days=30, daily_aggregation=True)

    assert len(report.chart_points) == 2
    first_day = report.chart_points[0]
    assert first_day.systolic == 120
    assert (first_day.systolic_min, first_day.systolic_max) == (110, 130)
    assert first_day.pulse == 70


@pytest.mark.parametrize("days,daily_aggregation", [(7, False), (30, True)])
def test_chart_renderer_returns_png(days, daily_aggregation):
    from app.chart_renderer import render_statistics_chart
    from app.health_statistics import build_statistics_report

    report = build_statistics_report(
        [
            _row("2026-07-20 08:00:00", 120, 80, 65),
            _row("2026-07-21 08:00:00", 125, 82, 70),
        ],
        days=days,
        daily_aggregation=daily_aggregation,
    )

    image = render_statistics_chart(report)

    assert image.read(8) == b"\x89PNG\r\n\x1a\n"
    assert image.name == f"statistics_{days}_days.png"
    image.close()


@pytest.mark.asyncio
async def test_statistics_period_menu(dummy_update, dummy_context):
    from app import measurement

    await measurement.get_day_statistics(dummy_update, dummy_context)

    assert dummy_update.callback_query.edited_texts[-1] == "Выберите период для сводки:"
    keyboard = dummy_update.callback_query.edit_kwargs[-1]["reply_markup"]
    callback_data = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert callback_data == ["statistics_week", "statistics_month", "statistics_back"]


@pytest.mark.asyncio
async def test_week_statistics_sends_photo(
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
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    db.insert("MeasureDetails", {
        "MeasurementID": measurement_id,
        "SystolicPressure": 120,
        "DiastolicPressure": 80,
        "Pulse": 70,
    })
    image = BytesIO(b"fake-png")
    image.name = "statistics.png"
    mocker.patch.object(measurement, "render_statistics_chart", return_value=image)
    dummy_update.callback_query.data = "statistics_week"

    await measurement.send_statistics_report(
        dummy_update, dummy_context, db_path=temp_db,
    )

    assert dummy_update.callback_query.message.photos == [b"fake-png"]
    photo_kwargs = dummy_update.callback_query.message.photo_kwargs[-1]
    caption = photo_kwargs["caption"]
    assert "Сводка за 7 дней" in caption
    assert "Медианное АД: 120/80" in caption
    assert "reply_markup" not in photo_kwargs
    assert dummy_update.callback_query.message.texts[-1] == (
        "Выберите следующее действие:"
    )
    menu = dummy_update.callback_query.message.kwargs[-1]["reply_markup"]
    callback_data = [button.callback_data for row in menu.inline_keyboard for button in row]
    assert "last_measurement" in callback_data
    assert "medication_intake" in callback_data
    assert image.closed


@pytest.mark.asyncio
async def test_statistics_reports_empty_period(
    temp_db, dummy_update, dummy_context,
):
    from app import measurement

    dummy_update.callback_query.data = "statistics_month"

    await measurement.send_statistics_report(
        dummy_update, dummy_context, db_path=temp_db,
    )

    assert dummy_update.callback_query.edited_texts[-1] == (
        "За последние 30 дней измерений нет."
    )
    assert dummy_update.callback_query.message.photos == []


@pytest.mark.asyncio
async def test_statistics_menu_replies_instead_of_editing_old_photo(
    dummy_update, dummy_context,
):
    from app import measurement

    dummy_update.callback_query.message.text = None

    await measurement.get_day_statistics(dummy_update, dummy_context)

    assert dummy_update.callback_query.edited_texts == []
    assert dummy_update.callback_query.message.texts[-1] == (
        "Выберите период для сводки:"
    )


@pytest.mark.asyncio
async def test_statistics_menu_ignores_unchanged_message(
    dummy_update, dummy_context, mocker,
):
    from telegram.error import BadRequest
    from app import measurement

    mocker.patch.object(
        dummy_update.callback_query,
        "edit_message_text",
        side_effect=BadRequest("Message is not modified"),
    )

    await measurement.get_day_statistics(dummy_update, dummy_context)
