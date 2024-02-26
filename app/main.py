import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

from logging_config import configure_logging
from handlers import start, help_command, echo
from measurement import start_add_measurement, blood_pressure, pulse, comment, body_position, arm_location
configure_logging()

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    app = Application.builder().token(TOKEN).build()

    questions_blood_pressure = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(Записать результат измерения)$'), start_add_measurement)],
        states={
            "blood_pressure": [MessageHandler(filters.TEXT, blood_pressure)],
            "pulse": [MessageHandler(filters.TEXT, pulse)],
            "body_position": [MessageHandler(filters.TEXT, body_position)],
            "arm_location": [MessageHandler(filters.TEXT, arm_location)],
            "comment": [MessageHandler(filters.TEXT, comment)],
        },
        fallbacks=[],
    )

    # on different commands - answer in Telegram
    app.add_handler(questions_blood_pressure)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
