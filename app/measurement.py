"""./app/measurement.py
Conversation flow and helpers for adding health measurements.

All user-facing messages remain in Russian (per product requirement), while
internal comments and docstrings are standardized in clear English.
"""
import logging
import re
import sqlite3
from typing import Callable, Awaitable

from telegram import InlineKeyboardMarkup, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes

from bot_messages import INPUT_PRESSURE, WRONG_PRESSURE, WRONG_PULSE
from keyboards import (
    BODY_POSITION_KEYBOARD,
    ARM_LOCATION_KEYBOARD,
    WLCOME_KEYBOARD,
    WELL_BEING_KEYBOARD,
    WITH_EDIT_BUTTON_KEYBOARD,
    EDIT_KEYBOARD,
    STATISTICS_PERIOD_KEYBOARD,
    EDIT_BODY_POSITION_KEYBOARD,
    EDIT_ARM_LOCATION_KEYBOARD,
    EDIT_WELL_BEING_KEYBOARD,
)

from logging_config import configure_logging
import db
from reference import (
    get_body_position_id,
    get_arm_location_id,
    get_well_being_id,
    get_body_position_name,
    get_arm_location_name,
    get_well_being_name,
)
from measurement_repository import MeasurementRepository
from message_formatter import render_edit_summary, render_last_measurement, render_receipt
from chart_renderer import render_statistics_chart
from health_statistics import build_statistics_report, format_statistics_caption

configure_logging()

logger = logging.getLogger(__name__)

EditHandler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[str]]


async def add_measurement(update: Update, data: dict) -> None:
    """Persist collected measurements to the database.

    Expects a dictionary in ``data['measurements']`` with keys: ``pressure``
    (list of two ints as strings), ``pulse`` (list with one int as string),
    ``body_position``, ``arm_location``, and ``comment``.
    """
    logger.info("Persist measurement: start user_id=%s", update.effective_user.id)
    # Support both dict with 'measurements' and context-like object with user_data
    if hasattr(data, 'user_data'):
        measurements = getattr(data, 'user_data', {}).get('measurements', {})
    else:
        measurements = data.get('measurements', {})
    pressure_list = measurements.get('pressure', [])
    pulse_list = measurements.get('pulse', [])
    body_position_text = measurements.get('body_position')
    arm_location_text = measurements.get('arm_location')
    well_being_text = measurements.get('well_being')
    comment_text = measurements.get('comment', '')

    try:
        systolic = int(pressure_list[0])
        diastolic = int(pressure_list[1])
        pulse = int(pulse_list[0])
    except (IndexError, ValueError, TypeError):
        logger.error("Invalid measurement payload: %s user_id=%s", measurements, update.effective_user.id)
        return

    body_position_id = get_body_position_id(body_position_text)
    arm_location_id = get_arm_location_id(arm_location_text)
    well_being_id = get_well_being_id(well_being_text)
    user = db.get_user(update.effective_user)
    user_id = user.get('UserID')

    repo = MeasurementRepository()
    with db.UnitOfWork(db.db_name) as uow:
        repo.insert_with_details(
            uow,
            user_id=user_id,
            systolic=systolic,
            diastolic=diastolic,
            pulse=pulse,
            body_position_id=body_position_id,
            arm_location_id=arm_location_id,
            well_being_id=well_being_id,
            comment_text=comment_text,
        )
    logger.info("Persist measurement: done user_id=%s", update.effective_user.id)


async def last_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE, db_path: str = None):
    """Fetch and show the last measurement for the current user."""
    user = db.get_user(update.effective_user)
    user_id = user.get('UserID')
    logger.info("Fetch last measurement for user_id=%s", user_id)
    # Simple join to get the latest measurement details
    row = MeasurementRepository().get_last_by_user(user_id, db_path)
    if not row:
        message = update.message or update.callback_query
        sender = message.reply_text if update.message else message.edit_message_text
        await sender(
            "Записей ещё нет.",
            reply_markup=InlineKeyboardMarkup(
                WLCOME_KEYBOARD
            ),
        )
        return

    id, ts, sys_p, dia_p, pulse, pos_name, arm_name, comment_text, well_being_name = row
    text = render_last_measurement(row)

    logger.info(f'Check update.message \n{update.message}\n{update}\n{dir(update)}')
    measurement_data = {
        'MeasurementID': id,
        'SystolicPressure': sys_p,
        'DiastolicPressure': dia_p,
        'Pulse': pulse,
        'PositionName': pos_name,
        'LocationName': arm_name,
        'Comments': comment_text,
        'WellBeing': well_being_name,
    }
    context.user_data['edit_measurement'] = measurement_data
    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            WITH_EDIT_BUTTON_KEYBOARD
        ),
    )


async def get_day_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, db_path: str = None):
    """Show available statistics periods."""
    await update.callback_query.edit_message_text(
        "Выберите период для сводки:",
        reply_markup=InlineKeyboardMarkup(STATISTICS_PERIOD_KEYBOARD),
    )


async def send_statistics_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_path: str = None,
):
    """Generate and send a weekly or monthly chart."""
    periods = {
        "statistics_week": (7, False),
        "statistics_month": (30, True),
    }
    period = periods.get(update.callback_query.data)
    if period is None:
        await update.callback_query.edit_message_text(
            "Неизвестный период.",
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        return

    days, daily_aggregation = period
    user_id = db.get_user(update.effective_user).get('UserID')
    rows = MeasurementRepository().list_since_days(
        user_id=user_id, days=days, database_path=db_path,
    )

    if not rows:
        await update.callback_query.edit_message_text(
            f"За последние {days} дней измерений нет.",
            reply_markup=InlineKeyboardMarkup(STATISTICS_PERIOD_KEYBOARD),
        )
        return

    report = build_statistics_report(
        rows, days=days, daily_aggregation=daily_aggregation,
    )
    image = render_statistics_chart(report)
    await update.callback_query.edit_message_text(
        "Сводка сформирована.",
        reply_markup=InlineKeyboardMarkup(STATISTICS_PERIOD_KEYBOARD),
    )
    try:
        await update.callback_query.message.reply_photo(
            photo=image,
            caption=format_statistics_caption(report),
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
    finally:
        image.close()


async def statistics_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return from the period selector to the main menu."""
    await update.callback_query.edit_message_text(
        "Главное меню:",
        reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )


def _render_edit_summary(measurement_data: dict) -> str:
    return render_edit_summary(measurement_data)


async def edit_last_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load the current user's latest measurement and open its editor."""
    await update.callback_query.answer()
    user_id = db.get_user(update.effective_user)['UserID']
    row = MeasurementRepository().get_last_by_user(user_id)
    if not row:
        await update.callback_query.edit_message_text(
            "Записей ещё нет.", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        return ConversationHandler.END
    measurement_data = {
        'MeasurementID': row[0],
        'SystolicPressure': row[2],
        'DiastolicPressure': row[3],
        'Pulse': row[4],
        'PositionName': row[5],
        'LocationName': row[6],
        'Comments': row[7],
        'WellBeing': row[8],
        '_dirty_fields': set(),
    }
    context.user_data['edit_measurement'] = measurement_data
    text = _render_edit_summary(measurement_data)
    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD),
    )
    return 'edit_choice_field'


async def edit_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith('set_'):
        return await apply_reference_choice(update, context)
    if handler := EDIT_HANDLERS.get(data):
        return await handler(update, context)
    logger.error("No handler for edit action: %s", data)
    await query.edit_message_text('Не найдена команда.')
    return 'edit_choice_field'


async def save_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save edited measurement data to database."""
    measurement_data = context.user_data.get('edit_measurement')
    if not measurement_data:
        await update.callback_query.edit_message_text('Сессия редактирования истекла.')
        return ConversationHandler.END
    logger.info("save_edit called for id=%s", measurement_data.get('MeasurementID'))

    try:
        # Update database with edited data
        user_id = db.get_user(update.effective_user)['UserID']
        update_measurement_in_db(measurement_data, user_id=user_id)

        await update.callback_query.edit_message_text(
            'Изменения сохранены.',
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        context.user_data.pop('edit_measurement', None)
    except (LookupError, ValueError, db.ConnectionError, sqlite3.Error) as exc:
        logger.error("Error saving edit: %s", exc)
        await update.callback_query.edit_message_text(
            'Ошибка при сохранении изменений. Попробуйте ещё раз.',
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )

    return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('edit_measurement', None)
    await update.callback_query.edit_message_text(
        'Редактирование отменено.', reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


async def cancel_edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel editing from a text-input state via /cancel."""
    context.user_data.pop('edit_measurement', None)
    await update.message.reply_text(
        'Редактирование отменено.',
        reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


async def edit_input_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to input new blood pressure values."""
    measurement_data = context.user_data['edit_measurement']
    current_pressure = f"{measurement_data.get('SystolicPressure')}/{measurement_data.get('DiastolicPressure')}"

    await update.callback_query.edit_message_text(
        (
            f"Текущее АД: {current_pressure}\n\n"
            "Введите новое артериальное давление в формате 'систолическое/диастолическое' "
            "(например: 120/80):"
        ),
        reply_markup=None,
    )
    return 'edit_pressure_input'


async def edit_pressure_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new blood pressure input and update measurement data."""
    pressure = re.findall(r"\d+", update.message.text)
    if len(pressure) != 2 or not (40 <= int(pressure[0]) <= 300) or not (20 <= int(pressure[1]) <= 200):
        await update.message.reply_text(WRONG_PRESSURE)
        return 'edit_pressure_input'

    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['SystolicPressure'] = int(pressure[0])
    measurement_data['DiastolicPressure'] = int(pressure[1])
    measurement_data['_dirty_fields'].update({'pressure'})

    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_input_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to input new pulse value."""
    measurement_data = context.user_data['edit_measurement']
    current_pulse = measurement_data.get('Pulse')

    await update.callback_query.edit_message_text(
        f"Текущий пульс: {current_pulse}\n\nВведите новый пульс:",
        reply_markup=None
    )
    return 'edit_pulse_input'


async def edit_pulse_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new pulse input and update measurement data."""
    pulse = re.findall(r"\d+", update.message.text)
    if len(pulse) != 1 or not (20 <= int(pulse[0]) <= 250):
        await update.message.reply_text(WRONG_PULSE)
        return 'edit_pulse_input'

    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['Pulse'] = int(pulse[0])
    measurement_data['_dirty_fields'].add('pulse')

    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_choose_body_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to select new body position."""
    measurement_data = context.user_data['edit_measurement']
    current_position = measurement_data.get('PositionName', 'Не указано')

    await update.callback_query.edit_message_text(
        f"Текущее положение: {current_position}\n\nВыберите новое положение:",
        reply_markup=InlineKeyboardMarkup(EDIT_BODY_POSITION_KEYBOARD),
    )
    return 'edit_choice_field'


async def edit_choose_arm_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to select new arm location."""
    measurement_data = context.user_data['edit_measurement']
    current_location = measurement_data.get('LocationName', 'Не указано')

    await update.callback_query.edit_message_text(
        f"Текущее положение манжеты: {current_location}\n\nВыберите новое положение манжеты:",
        reply_markup=InlineKeyboardMarkup(EDIT_ARM_LOCATION_KEYBOARD),
    )
    return 'edit_choice_field'


async def edit_choose_well_being(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to select new well-being status."""
    measurement_data = context.user_data['edit_measurement']
    current_wellbeing = measurement_data.get('WellBeing', 'Не указано')

    await update.callback_query.edit_message_text(
        f"Текущее самочувствие: {current_wellbeing}\n\nВыберите новое самочувствие:",
        reply_markup=InlineKeyboardMarkup(EDIT_WELL_BEING_KEYBOARD),
    )
    return 'edit_choice_field'


async def apply_reference_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apply a reference-table selection encoded in inline callback data."""
    action, raw_id = update.callback_query.data.split(':', 1)
    try:
        value_id = int(raw_id)
    except ValueError:
        await update.callback_query.edit_message_text('Некорректное значение.')
        return 'edit_choice_field'

    measurement_data = context.user_data['edit_measurement']
    choices = {
        'set_body_position': ('PositionName', 'body_position', get_body_position_name),
        'set_arm_location': ('LocationName', 'arm_location', get_arm_location_name),
        'set_well_being': ('WellBeing', 'well_being', get_well_being_name),
    }
    choice = choices.get(action)
    if choice is None:
        await update.callback_query.edit_message_text('Некорректное действие.')
        return 'edit_choice_field'
    field, dirty_field, lookup = choice
    name = lookup(value_id)
    if name is None:
        await update.callback_query.edit_message_text('Значение не найдено.')
        return 'edit_choice_field'
    measurement_data[field] = name
    measurement_data['_dirty_fields'].add(dirty_field)
    await update.callback_query.edit_message_text(
        _render_edit_summary(measurement_data),
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD),
    )
    return 'edit_choice_field'


async def edit_input_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to input new comment."""
    measurement_data = context.user_data['edit_measurement']
    current_comment = measurement_data.get('Comments', '—')

    await update.callback_query.edit_message_text(
        f"Текущий комментарий: {current_comment}\n\nВведите новый комментарий (или отправьте '—' для удаления):",
        reply_markup=None,
    )
    return 'edit_comment_input'


async def edit_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new comment input and update measurement data."""
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    new_comment = update.message.text if update.message.text != '—' else None
    measurement_data['Comments'] = new_comment
    measurement_data['_dirty_fields'].add('comment')

    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


def get_week_statistic():
    """Return aggregated statistics for the last week."""
    pass


def get_month_statistic():
    """Return aggregated statistics for the last month."""
    pass


def update_measurement_in_db(
    measurement_data: dict,
    *,
    user_id: int,
    database_path: str | None = None,
) -> None:
    """Update measurement data in the database."""
    measurement_id = measurement_data.get('MeasurementID')
    if not measurement_id:
        raise ValueError("No measurement ID provided for update")

    dirty = measurement_data.get('_dirty_fields', set())
    target_db = database_path or db.db_name

    body_position_id = (
        get_body_position_id(measurement_data.get('PositionName'), target_db)
        if 'body_position' in dirty else None
    )
    arm_location_id = (
        get_arm_location_id(measurement_data.get('LocationName'), target_db)
        if 'arm_location' in dirty else None
    )
    well_being_id = (
        get_well_being_id(measurement_data.get('WellBeing'), target_db)
        if 'well_being' in dirty else None
    )

    repo = MeasurementRepository()
    with db.UnitOfWork(target_db) as uow:
        remove_comment = (
            'comment' in dirty and (
                measurement_data.get('Comments') is None or
                not str(measurement_data.get('Comments')).strip()
            )
        )
        repo.update_measurement(
            uow,
            measurement_id=measurement_id,
            user_id=user_id,
            systolic=measurement_data.get('SystolicPressure') if 'pressure' in dirty else None,
            diastolic=measurement_data.get('DiastolicPressure') if 'pressure' in dirty else None,
            pulse=measurement_data.get('Pulse') if 'pulse' in dirty else None,
            body_position_id=body_position_id,
            arm_location_id=arm_location_id,
            well_being_id=well_being_id,
            comment_text=measurement_data.get('Comments') if 'comment' in dirty else None,
            remove_comment=remove_comment,
        )

    logger.info("Updated measurement id=%s", measurement_id)


EDIT_HANDLERS: dict[str, EditHandler] = {
    'save_edit': save_edit,
    'cancel_edit': cancel_edit,
    'edit_pressure': edit_input_pressure,
    'edit_pulse': edit_input_pulse,
    'edit_body_position': edit_choose_body_position,
    'edit_arm_location': edit_choose_arm_location,
    'edit_well_being': edit_choose_well_being,
    'edit_comment': edit_input_comment,
}


async def start_add_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the measurement conversation and prompt for blood pressure."""
    await update.callback_query.answer()
    logger.info("Start add measurement: user_id=%s chat_id=%s", update.effective_user.id, update.effective_chat.id)
    await update.effective_message.reply_text(
        INPUT_PRESSURE,
        reply_markup=ReplyKeyboardRemove(),
        )
    return "blood_pressure"


async def blood_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate and store systolic/diastolic pressure values from user's message."""
    pressure = re.findall(r"\d+", update.message.text)
    logger.info(f'Pressure: {type(pressure)}, {len(pressure)}, {pressure}')
    if len(pressure) != 2:
        logger.warning("Wrong pressure input: text='%s' user_id=%s", update.message.text, update.effective_user.id)
        await update.message.reply_text(WRONG_PRESSURE)
        return "blood_pressure"
    context.user_data['measurements'] = {'pressure': pressure}
    logger.info("Accepted pressure: %s/%s user_id=%s", pressure[0], pressure[1], update.effective_user.id)
    await update.message.reply_text(f'Ок, так и запишим {pressure[0]} на {pressure[1]},\nА какой пульс?')
    return "pulse"


async def pulse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate and store pulse value; prompt for body position selection."""
    pulse = re.findall(r"\d+", update.message.text)
    if len(pulse) != 1:
        logger.warning("Wrong pulse input: text='%s' user_id=%s", update.message.text, update.effective_user.id)
        await update.message.reply_text(WRONG_PULSE)
        return "pulse"
    reply_markup = ReplyKeyboardMarkup(BODY_POSITION_KEYBOARD, resize_keyboard=True)
    context.user_data['measurements']['pulse'] = pulse
    logger.info("Accepted pulse: %s user_id=%s", pulse[0], update.effective_user.id)
    await update.message.reply_text(
        f'Ок, так и запишим ваш пульс {pulse[0]}.\n'
        'Выбери положение при котором происходил замер.',
        reply_markup=reply_markup
    )
    return "body_position"


async def body_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save body position and prompt for arm location using keyboard."""
    context.user_data['measurements']['body_position'] = update.message.text
    logger.info("Selected body_position: %s user_id=%s", update.message.text, update.effective_user.id)
    reply_markup = ReplyKeyboardMarkup(ARM_LOCATION_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "Выбери положение манжеты на руке.", reply_markup=reply_markup
    )
    return "arm_location"


async def arm_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save arm location and ask for user's additional comments."""
    context.user_data['measurements']['arm_location'] = update.message.text
    logger.info("Selected arm_location: %s user_id=%s", update.message.text, update.effective_user.id)

    reply_markup = ReplyKeyboardMarkup(WELL_BEING_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "Как самочувствие?",
        reply_markup=reply_markup
    )
    return "well_being"


async def well_being(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['measurements']['well_being'] = update.message.text
    logger.info("Selected well_being: %s user_id=%s", update.message.text, update.effective_user.id)
    await update.message.reply_text(
        "Любые жалобы или заметки? (можно пропустить)",
        reply_markup=ReplyKeyboardRemove()
    )
    return "comment"


async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalize collection, persist data, and end the conversation."""
    context.user_data['measurements']['comment'] = update.message.text
    query = context.user_data['measurements']
    logger.info(f'type query:{query}')
    await add_measurement(update, context.user_data)
    receipt = render_receipt(query)
    logger.info("Send receipt to user_id=%s: %s", update.effective_user.id, receipt.replace('\n', ' | '))
    await update.message.reply_text(
        receipt,
        reply_markup=InlineKeyboardMarkup(
            WLCOME_KEYBOARD
        ),
    )
    return ConversationHandler.END
