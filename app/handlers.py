import logging
from html import escape
from uuid import uuid4

from telegram import (
                    Update,
                    InlineQueryResultArticle,
                    InputTextMessageContent,
                    InlineKeyboardButton,
                    InlineKeyboardMarkup,
                    )
from telegram.constants import ParseMode
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
    reply_markup = InlineKeyboardMarkup(WLCOME_KEYBOARD)
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    logger.info("User click help")
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    logger.info("User send message")
    await update.message.reply_text(update.message.text)


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline query. This is run when you type: @botusername <query>"""
    query = update.inline_query.query
    if not query:  # empty query should not be handled
        return
    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Caps",
            input_message_content=InputTextMessageContent(query.upper()),
        ),
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Bold",
            input_message_content=InputTextMessageContent(
                f"<b>{escape(query)}</b>", parse_mode=ParseMode.HTML
            ),
        ),
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Italic",
            input_message_content=InputTextMessageContent(
                f"<i>{escape(query)}</i>", parse_mode=ParseMode.HTML
            ),
        ),
    ]
    await update.inline_query.answer(results)
