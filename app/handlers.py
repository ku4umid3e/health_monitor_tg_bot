"""./app/handlers.py
Command and message handlers for the Telegram bot.

Docstrings are unified in English; user-visible texts remain in Russian.
"""
import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot_messages import WELCOME_MESSAGE
from keyboards import WLCOME_KEYBOARD
from measurement import last_measurement, get_day_statistics
import db
from logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

CALLBACK_HANDLERS = {
    'last_measurement': last_measurement,
    'get_day_statistics': get_day_statistics,
}


def greate_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ensure user exists in DB and log greeting event."""
    logger.info(f"Grate user{update.effective_user}, {update.message.chat.id}")
    print("User pressed start", type(update.effective_user.id), update.effective_user.id)
    user = db.get_user(update.effective_user)
    print('user in db', type(user), user)
    logger.info(f"in db user = {user}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and show the main keyboard."""
    greate_user(update=update, context=context)
    await update.message.reply_text(
        WELCOME_MESSAGE, reply_markup=InlineKeyboardMarkup(
            WLCOME_KEYBOARD)
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond to /help with a short help message."""
    logger.info("User click help")
    await update.message.reply_text("Help!")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unhandled exceptions and, if possible, notify the user."""
    logger.exception("Unhandled exception: %s", context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла сетевая ошибка. Попробуйте ещё раз, пожалуйста."
            )
    except Exception as inner_err:  # noqa: BLE001
        logger.error("Failed to notify user about error: %s", inner_err)


async def button_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses from inline keyboards."""
    logger.info(f'Button_handler activate {update.callback_query.data}')
    query = update.callback_query
    await query.answer()

    handler = CALLBACK_HANDLERS.get(query.data)
    if handler:
        return await handler(update, context)
    logger.warning(f"Unhandled callback data: {query.data}")
    await query.edit_message_text('Error: Unknow command!')
