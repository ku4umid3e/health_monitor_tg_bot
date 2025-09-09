"""Conversation flow and helpers for adding health measurements.

All user-facing messages remain in Russian (per product requirement), while
internal comments and docstrings are standardized in clear English.
"""
import logging
import re

from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes

from bot_messages import INPUT_PRESSURE, WRONG_PRESSURE, WRONG_PULSE
from keyboard import BODY_POSITION_KEYBOARD, ARM_LOCATION_KEYBOARD

from logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)


async def add_measurement(data: dict) -> None:
    """Persist collected measurements to the database.

    Expects a dictionary in ``data['measurements']`` with keys: ``pressure``
    (list of two ints as strings), ``pulse`` (list with one int as string),
    ``body_position``, ``arm_location``, and ``comment``.
    """
    pass


def last_measurement():
    """Return the last saved measurement for the current user."""
    pass


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
        await update.message.reply_text(WRONG_PRESSURE)
        return "blood_pressure"
    context.user_data['measurements'] = {'pressure': pressure}
    await update.message.reply_text(f'Ок, так и запишим {pressure[0]} на {pressure[1]},\nА какой пульс?')
    return "pulse"


async def pulse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate and store pulse value; prompt for body position selection."""
    pulse = re.findall(r"\d+", update.message.text)
    if len(pulse) != 1:
        await update.message.reply_text(WRONG_PULSE)
        return "pulse"
    reply_markup = ReplyKeyboardMarkup(BODY_POSITION_KEYBOARD, resize_keyboard=True)
    context.user_data['measurements']['pulse'] = pulse
    await update.message.reply_text(
        f'Ок, так и запишим ваш пульс {pulse[0]}.\n'
        'Выбери положение при котором происходил замер.',
        reply_markup=reply_markup
    )
    return "body_position"


async def body_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save body position and prompt for arm location using keyboard."""
    context.user_data['measurements']['body_position'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(ARM_LOCATION_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "Выбери положение манжеты на руке.", reply_markup=reply_markup
    )
    return "arm_location"


async def arm_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save arm location and ask for user's additional comments."""
    context.user_data['measurements']['arm_location'] = update.message.text

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
    await update.message.reply_text('Супер! Я записал.(НЕТ)')
    await add_measurement(context.user_data)
    return ConversationHandler.END
