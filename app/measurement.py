# import db
import logging
import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ConversationHandler, ContextTypes

from bot_messages import INPUT_PRESSURE, WRONG_PRESSURE, WRONG_PULSE

from logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)


def add_measurement():
    pass


def last_measurement():
    pass


def get_day_statistics():
    pass


def get_week_statistic():
    pass


def get_month_statistic():
    pass


async def start_add_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding measurement. Tells the user how to fill out the form correctly"""
    await update.message.reply_text(
        INPUT_PRESSURE,
        reply_markup=ReplyKeyboardRemove(),
        )
    return "blood_pressure"


async def blood_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function processes the result of the user's water."""
    pressure = re.findall(r"\d+", update.message.text)
    logger.info(f'Pressure: {type(pressure)}, {len(pressure)}, {pressure}')    
    if len(pressure) != 2:
        await update.message.reply_text(WRONG_PRESSURE)
        return "blood_pressure"
    context.user_data['measurements'] = {'pressure': pressure}
    await update.message.reply_text(f'Ок, так и запишим {pressure[0]} на {pressure[1]},\nА какой пульс?')
    return "pulse"


async def pulse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function processes the result of the user's water."""
    pulse = re.findall(r"\d+", update.message.text)
    if len(pulse) != 1:
        await update.message.reply_text(WRONG_PULSE)
        return "pulse"
    
    context.user_data['measurements'] = {'pulse': pulse}
    await update.message.reply_text(
        f'Ок, так и запишим ваш пульс {pulse[0]}.\n' \
        'Опишите своё самочуствие(хорошое или плохое, а может что-то болит?).'
    )
    return "comment"


async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    """
    context.user_data['measurements'] = {'comment': update.message.text}
    await update.message.reply_text('Супер! Я записал.')
    return ConversationHandler.END
