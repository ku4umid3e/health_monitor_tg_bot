import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from bot_messages import WELCOME_MESSAGE
from keyboard import WLCOME_KEYBOARD
import db
from logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)


def greate_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Grate user{update.effective_user}, {update.message.chat.id}")
    print("User pressed start", type(update.effective_user.id), update.effective_user.id)
    user = db.get_user(update.effective_user)
    print('user in db', type(user), user)
    logger.info(f"in db user = {user}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with three inline buttons attached."""
    greate_user(update=update, context=context)
    await update.message.reply_text(
        WELCOME_MESSAGE, reply_markup=ReplyKeyboardMarkup(
            WLCOME_KEYBOARD,
            one_time_keyboard=True,
            resize_keyboard=True,
            )
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    logger.info("User click help")
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    logger.info("User send message")
    await update.message.reply_text(update.message.text)
