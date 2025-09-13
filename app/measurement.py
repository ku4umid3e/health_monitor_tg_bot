"""Conversation flow and helpers for adding health measurements.

All user-facing messages remain in Russian (per product requirement), while
internal comments and docstrings are standardized in clear English.
"""
import logging
import re

from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes

from bot_messages import INPUT_PRESSURE, WRONG_PRESSURE, WRONG_PULSE
from keyboard import BODY_POSITION_KEYBOARD, ARM_LOCATION_KEYBOARD, WLCOME_KEYBOARD

from logging_config import configure_logging
import db
from db import UseDB, db_name

configure_logging()

logger = logging.getLogger(__name__)


async def add_measurement(update: Update, data: dict) -> None:
    """Persist collected measurements to the database.

    Expects a dictionary in ``data['measurements']`` with keys: ``pressure``
    (list of two ints as strings), ``pulse`` (list with one int as string),
    ``body_position``, ``arm_location``, and ``comment``.
    """
    logger.info("Persist measurement: start user_id=%s", update.effective_user.id)
    # Support both dict with 'measurements' and context-like object with user_data
    if hasattr(data, 'user_data') and isinstance(data.user_data, dict):
        measurements = data.user_data.get('measurements', {})
    elif isinstance(data, dict):
        measurements = data.get('measurements', {})
    else:
        measurements = {}
    pressure_list = measurements.get('pressure', [])
    pulse_list = measurements.get('pulse', [])
    body_position_text = measurements.get('body_position')
    arm_location_text = measurements.get('arm_location')
    comment_text = measurements.get('comment', '')

    try:
        systolic = int(pressure_list[0])
        diastolic = int(pressure_list[1])
        pulse = int(pulse_list[0])
    except (IndexError, ValueError, TypeError):
        logger.error("Invalid measurement payload: %s user_id=%s", measurements, update.effective_user.id)
        return

    body_position_map = {
        'Стоя': 1,
        'Сидя': 2,
        'Лёжа': 3,
        'Полу лёжа': 4,
        'Не указано': 5,
    }
    arm_location_map = {
        'Левая рука': 1,
        'Правая рука': 2,
        'Левое плечё': 3,
        'Правое плечё': 4,
        'Не указано': 5,
    }

    body_position_id = body_position_map.get(body_position_text, 5)
    arm_location_id = arm_location_map.get(arm_location_text, 5)

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
    query = (
        "SELECT M.MeasurementID, M.Timestamp, MD.SystolicPressure, MD.DiastolicPressure, MD.Pulse, "
        "BP.PositionName, AL.LocationName, C.CommentText "
        "FROM Measurements M "
        "JOIN MeasureDetails MD ON MD.MeasurementID = M.MeasurementID "
        "LEFT JOIN BodyPositions BP ON BP.BodyPositionID = M.BodyPositionID "
        "LEFT JOIN ArmLocation AL ON AL.ArmLocationID = M.ArmLocationID "
        "LEFT JOIN Comments C ON C.CommentID = M.CommentID "
        "WHERE M.UserID = ? "
        "ORDER BY M.Timestamp DESC LIMIT 1"
    )

    # Use provided db_path or fallback to global db_name
    target_db = db_path or db_name
    with UseDB(target_db) as cursor:
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()

    if not row:
        await update.message.reply_text(
            "Записей ещё нет.",
            reply_markup=ReplyKeyboardMarkup(
                WLCOME_KEYBOARD,
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return

    _, ts, sys_p, dia_p, pulse, pos_name, arm_name, comment_text = row
    text = (
        "Последнее измерение:\n"
        f"Дата/время: {ts}\n"
        f"АД: {sys_p}/{dia_p}, Пульс: {pulse}\n"
        f"Положение: {pos_name or 'Не указано'}, Манжета: {arm_name or 'Не указано'}\n"
        f"Комментарий: {comment_text or '—'}"
    )
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(
            WLCOME_KEYBOARD,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )


def get_day_statistics():
    """Return aggregated statistics for the last day."""
    pass


def get_week_statistic():
    """Return aggregated statistics for the last week."""
    pass


def get_month_statistic():
    """Return aggregated statistics for the last month."""
    pass


async def start_add_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the measurement conversation and prompt for blood pressure."""
    logger.info("Start add measurement: user_id=%s chat_id=%s", update.effective_user.id, update.message.chat.id)
    await update.message.reply_text(
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

    await update.message.reply_text(
        "Последний вопрос, как самочуствие?\n(Любые жалобы).",
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
        f"Комментарий: {query['comment']}"
    )
    logger.info("Send receipt to user_id=%s: %s", update.effective_user.id, receipt.replace('\n', ' | '))
    await update.message.reply_text(
        receipt,
        reply_markup=ReplyKeyboardMarkup(
            WLCOME_KEYBOARD,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return ConversationHandler.END
