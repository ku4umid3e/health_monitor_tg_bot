"""./app/main.py
Application entrypoint for the Telegram bot."""
import os
import logging

from telegram import CallbackQuery, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.request import HTTPXRequest

from logging_config import configure_logging
from handlers import (
    start,
    help_command,
    error_handler,
    button_handlers,
)
from measurement import (
    start_add_measurement,
    blood_pressure,
    pulse,
    comment,
    body_position,
    arm_location,
    well_being,
    edit_last_measurement,
    edit_menu_click,
    edit_pressure_input,
    edit_pulse_input,
    edit_comment_input,
    cancel_edit_command,
    cancel_add_measurement,
)
from medication import (
    arbitrary_dose,
    arbitrary_name,
    cancel_text_flow,
    edit_comment as edit_medication_comment,
    edit_time as edit_medication_time,
    intake_choice,
    medication_done,
    save_one_off,
    settings_choice,
    settings_dose,
    settings_name,
    settings_schedule,
    start_edit_comment,
    start_edit_time,
    start_medication_intake,
    start_medication_settings,
    undo_intake,
)
configure_logging()

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
PROXY_URL = os.getenv("PROXY_URL") or None


def build_request() -> HTTPXRequest:
    """Create a Telegram HTTP client with the optional shared proxy."""
    return HTTPXRequest(
        proxy_url=PROXY_URL,
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=30.0,
    )


def main() -> None:
    """Start the bot application and register handlers."""
    # Configure HTTPX client with timeouts to improve network resilience
    builder = Application.builder().token(TOKEN)
    app = (
        builder
        .request(build_request())
        .get_updates_request(build_request())
        .build()
    )

    questions_blood_pressure = ConversationHandler(
        entry_points=[
            # MessageHandler(filters.Regex('^(Записать результат измерения)$'), start_add_measurement),
            CallbackQueryHandler(start_add_measurement, pattern='^add_measurement$')
            ],
        states={
            "blood_pressure": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_add_measurement),
                MessageHandler(filters.TEXT, blood_pressure),
            ],
            "pulse": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_add_measurement),
                MessageHandler(filters.TEXT, pulse),
            ],
            "body_position": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_add_measurement),
                MessageHandler(filters.TEXT, body_position),
            ],
            "arm_location": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_add_measurement),
                MessageHandler(filters.TEXT, arm_location),
            ],
            "well_being": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_add_measurement),
                MessageHandler(filters.TEXT, well_being),
            ],
            "comment": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_add_measurement),
                MessageHandler(filters.TEXT, comment),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_measurement)],
        per_chat=True,
        per_user=True,
    )

    edit_last_measurement_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_last_measurement, pattern='^edit_last_measurement$')
            ],
        states={
            "edit_choice_field": [
                CallbackQueryHandler(edit_menu_click, pattern='^(edit_.*|set_.*|save_edit|cancel_edit)$')
                ],
            "edit_pressure_input": [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_pressure_input)],
            "edit_pulse_input": [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_pulse_input)],
            "edit_comment_input": [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_comment_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit_command)],
        per_chat=True,
        per_user=True,
    )

    medication_intake_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_medication_intake, pattern='^medication_intake$'),
            CallbackQueryHandler(start_edit_time, pattern=r'^med_time:\d+$'),
            CallbackQueryHandler(start_edit_comment, pattern=r'^med_comment:\d+$'),
            CallbackQueryHandler(undo_intake, pattern=r'^med_undo:\d+$'),
            CallbackQueryHandler(save_one_off, pattern=r'^med_save:\d+$'),
            CallbackQueryHandler(medication_done, pattern='^med_done$'),
        ],
        states={
            "intake_choice": [
                CallbackQueryHandler(intake_choice, pattern=r'^(med_take:\d+|med_other|med_cancel)$'),
            ],
            "intake_name": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, arbitrary_name),
            ],
            "intake_dose": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, arbitrary_dose),
            ],
            "edit_intake_time": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_medication_time),
            ],
            "edit_intake_comment": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_medication_comment),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_text_flow)],
        per_chat=True,
        per_user=True,
    )

    medication_settings_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_medication_settings, pattern='^medication_settings$'),
        ],
        states={
            "settings_menu": [CallbackQueryHandler(
                settings_choice,
                pattern=r'^(med_add|med_settings_done|med_toggle:\d+|med_archive:\d+)$',
            )],
            "settings_name": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_name),
            ],
            "settings_dose": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_dose),
            ],
            "settings_schedule": [
                MessageHandler(filters.Regex('^Отмена$'), cancel_text_flow),
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_schedule),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_text_flow)],
        per_chat=True,
        per_user=True,
    )

    # Register command handlers
    app.add_handler(questions_blood_pressure)
    app.add_handler(edit_last_measurement_conversation)
    app.add_handler(medication_intake_conversation)
    app.add_handler(medication_settings_conversation)
    app.add_handler(CallbackQueryHandler(button_handlers))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Register global error handler
    app.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
