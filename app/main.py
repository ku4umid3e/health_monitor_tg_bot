"""Application entrypoint for the Telegram bot."""
import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.request import HTTPXRequest

from logging_config import configure_logging
from handlers import start, help_command, echo, error_handler
from measurement import (
    start_add_measurement,
    blood_pressure,
    pulse,
    comment,
    body_position,
    arm_location,
    well_being,
    last_measurement,
    get_day_statistics
)
configure_logging()

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")


def main() -> None:
    """Start the bot application and register handlers."""
    # Configure HTTPX client with timeouts to improve network resilience
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=30.0,
    )
    # Create the Application and pass it your bot's token and custom request
    app = Application.builder().token(TOKEN).request(request).build()

    questions_blood_pressure = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(Записать результат измерения)$'), start_add_measurement)],
        states={
            "blood_pressure": [MessageHandler(filters.TEXT, blood_pressure)],
            "pulse": [MessageHandler(filters.TEXT, pulse)],
            "body_position": [MessageHandler(filters.TEXT, body_position)],
            "arm_location": [MessageHandler(filters.TEXT, arm_location)],
            "well_being": [MessageHandler(filters.TEXT, well_being)],
            "comment": [MessageHandler(filters.TEXT, comment)],
        },
        fallbacks=[],
    )

    # Register command handlers
    app.add_handler(questions_blood_pressure)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("last", last_measurement))
    app.add_handler(CommandHandler("daystat", get_day_statistics))
    # Register button handler for "Посмотреть последний результат"
    app.add_handler(MessageHandler(filters.Regex('^(Посмотреть последний результат)$'), last_measurement))

    # Echo back non-command messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Register global error handler
    app.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
