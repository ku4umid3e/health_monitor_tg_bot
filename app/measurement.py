"""./app/measurement.py
Conversation flow and helpers for adding health measurements.

All user-facing messages remain in Russian (per product requirement), while
internal comments and docstrings are standardized in clear English.
"""
import logging
import re
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
)

from logging_config import configure_logging
import db
from reference import (
    get_body_position_id,
    get_arm_location_id,
    get_well_being_id,
)

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

    comment_id = None
    if comment_text and comment_text.strip():
        comment_id = db.insert('Comments', {'CommentText': comment_text.strip()})
        logger.info("Inserted comment id=%s user_id=%s", comment_id, update.effective_user.id)

    measurement_id = db.insert('Measurements', {
        'UserID': user_id,
        'ArmLocationID': arm_location_id,
        'BodyPositionID': body_position_id,
        'WellBeingID': well_being_id,
        'CommentID': comment_id,
    })
    logger.info("Inserted measurement id=%s user_id=%s", measurement_id, update.effective_user.id)

    details_id = db.insert('MeasureDetails', {
        'MeasurementID': measurement_id,
        'SystolicPressure': systolic,
        'DiastolicPressure': diastolic,
        'Pulse': pulse,
    })
    logger.info("Inserted measure details id=%s for measurement id=%s",
                details_id, measurement_id)
    logger.info("User context for details: user_id=%s", update.effective_user.id)
    logger.info("Persist measurement: done user_id=%s", update.effective_user.id)


async def last_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE, db_path: str = None):
    """Fetch and show the last measurement for the current user."""
    user = db.get_user(update.effective_user)
    user_id = user.get('UserID')
    logger.info("Fetch last measurement for user_id=%s", user_id)
    # Simple join to get the latest measurement details
    row = db.fetch_last_measurement(user_id)
    if not row:
        await update.message.reply_text(
            "Записей ещё нет.",
            reply_markup=InlineKeyboardMarkup(
                WLCOME_KEYBOARD
            ),
        )
        return

    id, ts, sys_p, dia_p, pulse, pos_name, arm_name, comment_text, well_being_name = row
    text = (
        "Последнее измерение:\n"
        f"Дата/время: {ts}\n"
        f"АД: {sys_p}/{dia_p}, Пульс: {pulse}\n"
        f"Положение: {pos_name or 'Не указано'}, Манжета: {arm_name or 'Не указано'}\n"
        f"Самочувствие: {well_being_name or 'Не указано'}\n"
        f"Комментарий: {comment_text or '—'}"
    )

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
    """Return aggregated statistics for the last day."""
    user_id = db.get_user(update.effective_user).get('UserID')
    rows = db.fetch_measurements_since_days(user_id=user_id, days=3)

    if not rows:
        await update.callback_query.edit_message_text(
            "Записей ещё нет, либо они старше 3х дней.",
            reply_markup=InlineKeyboardMarkup(
                WLCOME_KEYBOARD
            ),
        )
        return

    text = '📊 Измерения за 3 дня:\n\n'

    current_day = None
    for row in rows:
        _, ts, sys, dia, pls, pos, arm, com, well_being_name = row
        day = ts.split()[0] if isinstance(ts, str) else str(ts)
        if day != current_day:
            current_day = day
            text += f'\n📅 {current_day}\n'
        time_part = ts.split()[1][:5] if isinstance(ts, str) else str(ts)
        text += f'  ⏰ {time_part} - АД: {sys}/{dia}, Пульс: {pls}, Самочувствие: {well_being_name or "Не указано"}\n'

    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            WLCOME_KEYBOARD
        ),
    )


def _render_edit_summary(measurement_data: dict) -> str:
    return (
        "Изменение последнего измерения:\n"
        f"АД: {measurement_data.get('SystolicPressure')}/{measurement_data.get('DiastolicPressure')}, "
        f"Пульс: {measurement_data.get('Pulse')}\n"
        f"Положение: {measurement_data.get('PositionName') or 'Не указано'}, "
        f"Манжета: {measurement_data.get('LocationName') or 'Не указано'}\n"
        f"Самочувствие: {measurement_data.get('WellBeing') or 'Не указано'}\n"
        f"Комментарий: {measurement_data.get('Comments') or '—'}"
    )


async def edit_last_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit the last measurement."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
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
    if handler := EDIT_HANDLERS.get(data):
        return await handler(update, context)
    logger.error("No handler for edit action: %s", data)
    await query.edit_message_text('Не найдена команда.')
    return 'edit_choice_field'


async def save_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save edited measurement data to database."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
    logger.info("save_edit called for id=%s", measurement_data.get('MeasurementID'))
    
    try:
        # Update database with edited data
        update_measurement_in_db(measurement_data)
        
        await update.callback_query.edit_message_text(
            'Изменения сохранены.', 
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
    except Exception as e:
        logger.error("Error saving edit: %s", e)
        await update.callback_query.edit_message_text(
            'Ошибка при сохранении изменений. Попробуйте ещё раз.',
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
    
    return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        'Редактирование отменено.', reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


async def edit_input_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to input new blood pressure values."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
    current_pressure = f"{measurement_data.get('SystolicPressure')}/{measurement_data.get('DiastolicPressure')}"
    
    await update.callback_query.edit_message_text(
        f"Текущее АД: {current_pressure}\n\nВведите новое артериальное давление в формате 'систолическое/диастолическое' (например: 120/80):",
        reply_markup=None
    )
    return 'edit_pressure_input'


async def edit_pressure_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new blood pressure input and update measurement data."""
    pressure = re.findall(r"\d+", update.message.text)
    if len(pressure) != 2:
        await update.message.reply_text(WRONG_PRESSURE)
        return 'edit_pressure_input'
    
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['SystolicPressure'] = int(pressure[0])
    measurement_data['DiastolicPressure'] = int(pressure[1])
    
    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_input_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to input new pulse value."""
    await update.callback_query.answer()
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
    if len(pulse) != 1:
        await update.message.reply_text(WRONG_PULSE)
        return 'edit_pulse_input'
    
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['Pulse'] = int(pulse[0])
    
    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_choose_body_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to select new body position."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
    current_position = measurement_data.get('PositionName', 'Не указано')
    
    await update.callback_query.edit_message_text(
        f"Текущее положение: {current_position}\n\nВыберите новое положение:",
        reply_markup=ReplyKeyboardMarkup(BODY_POSITION_KEYBOARD, resize_keyboard=True)
    )
    return 'edit_body_position_input'


async def edit_body_position_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new body position selection and update measurement data."""
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['PositionName'] = update.message.text
    
    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_choose_arm_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to select new arm location."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
    current_location = measurement_data.get('LocationName', 'Не указано')
    
    await update.callback_query.edit_message_text(
        f"Текущее положение манжеты: {current_location}\n\nВыберите новое положение манжеты:",
        reply_markup=ReplyKeyboardMarkup(ARM_LOCATION_KEYBOARD, resize_keyboard=True)
    )
    return 'edit_arm_location_input'


async def edit_arm_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new arm location selection and update measurement data."""
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['LocationName'] = update.message.text
    
    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_choose_well_being(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to select new well-being status."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
    current_wellbeing = measurement_data.get('WellBeing', 'Не указано')
    
    await update.callback_query.edit_message_text(
        f"Текущее самочувствие: {current_wellbeing}\n\nВыберите новое самочувствие:",
        reply_markup=ReplyKeyboardMarkup(WELL_BEING_KEYBOARD, resize_keyboard=True)
    )
    return 'edit_well_being_input'


async def edit_well_being_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new well-being selection and update measurement data."""
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    measurement_data['WellBeing'] = update.message.text
    
    # Show updated summary and return to edit menu
    text = _render_edit_summary(measurement_data)
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(EDIT_KEYBOARD)
    )
    return 'edit_choice_field'


async def edit_input_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to input new comment."""
    await update.callback_query.answer()
    measurement_data = context.user_data['edit_measurement']
    current_comment = measurement_data.get('Comments', '—')
    
    await update.callback_query.edit_message_text(
        f"Текущий комментарий: {current_comment}\n\nВведите новый комментарий (или отправьте '—' для удаления):",
        reply_markup=ReplyKeyboardRemove()
    )
    return 'edit_comment_input'


async def edit_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new comment input and update measurement data."""
    # Update measurement data
    measurement_data = context.user_data['edit_measurement']
    new_comment = update.message.text if update.message.text != '—' else None
    measurement_data['Comments'] = new_comment
    
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


def update_measurement_in_db(measurement_data: dict) -> None:
    """Update measurement data in the database."""
    measurement_id = measurement_data.get('MeasurementID')
    if not measurement_id:
        logger.error("No measurement ID provided for update")
        return
    
    # Update MeasureDetails table
    db.update('MeasureDetails', measurement_id, {
        'SystolicPressure': measurement_data.get('SystolicPressure'),
        'DiastolicPressure': measurement_data.get('DiastolicPressure'),
        'Pulse': measurement_data.get('Pulse'),
    }, 'MeasurementID')
    
    # Update Measurements table with reference IDs
    updates = {}
    
    # Get reference IDs for updated values
    if measurement_data.get('PositionName'):
        updates['BodyPositionID'] = get_body_position_id(measurement_data['PositionName'])
    
    if measurement_data.get('LocationName'):
        updates['ArmLocationID'] = get_arm_location_id(measurement_data['LocationName'])
    
    if measurement_data.get('WellBeing'):
        updates['WellBeingID'] = get_well_being_id(measurement_data['WellBeing'])
    
    # Handle comment update
    if 'Comments' in measurement_data:
        comment_text = measurement_data.get('Comments')
        if comment_text and comment_text.strip():
            # Create new comment
            comment_id = db.insert('Comments', {'CommentText': comment_text.strip()})
            updates['CommentID'] = comment_id
        else:
            # Remove comment
            updates['CommentID'] = None
    
    if updates:
        db.update('Measurements', measurement_id, updates, 'MeasurementID')
    
    logger.info("Updated measurement id=%s with data: %s", measurement_id, updates)


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
    receipt = (
        'Супер! Я записал измерение:\n'
        f"АД: {query['pressure'][0]}/{query['pressure'][1]}, Пульс: {query['pulse'][0]}\n"
        f"Положение: {query['body_position']}, Манжета: {query['arm_location']}\n"
        f"Самочувствие: {query['well_being']}\n"
        f"Комментарий: {query['comment']}"
    )
    logger.info("Send receipt to user_id=%s: %s", update.effective_user.id, receipt.replace('\n', ' | '))
    await update.message.reply_text(
        receipt,
        reply_markup=InlineKeyboardMarkup(
            WLCOME_KEYBOARD
        ),
    )
    return ConversationHandler.END
