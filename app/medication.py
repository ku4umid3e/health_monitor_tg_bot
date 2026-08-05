"""Telegram flows for medication settings and medication-intake events."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

import db
from doctor_report import MOSCOW_TZ, utc_to_moscow
from keyboards import CANCEL_KEYBOARD, SKIP_TEXT, WLCOME_KEYBOARD
from medication_repository import MedicationRepository


repo = MedicationRepository()


def _user_id(update: Update) -> int:
    return db.get_user(update.effective_user)["UserID"]


def _intake_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for medication_id, name, dose, _schedule, is_quick in repo.list_active(user_id):
        if is_quick:
            label = f"{name} {dose}" if dose else name
            rows.append([InlineKeyboardButton(label, callback_data=f"med_take:{medication_id}")])
    rows.extend([
        [InlineKeyboardButton("Другое лекарство", callback_data="med_other")],
        [InlineKeyboardButton("Отмена", callback_data="med_cancel")],
    ])
    return InlineKeyboardMarkup(rows)


def _receipt_keyboard(intake_id: int, *, can_save: bool = False) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton("Изменить время", callback_data=f"med_time:{intake_id}"),
        InlineKeyboardButton("Комментарий", callback_data=f"med_comment:{intake_id}"),
    ], [
        InlineKeyboardButton("Отменить запись", callback_data=f"med_undo:{intake_id}"),
    ]]
    if can_save:
        rows.append([InlineKeyboardButton(
            "Сохранить в мои лекарства", callback_data=f"med_save:{intake_id}",
        )])
    rows.append([InlineKeyboardButton("Главное меню", callback_data="med_done")])
    return InlineKeyboardMarkup(rows)


def _format_intake(row: tuple) -> str:
    _id, _medication_id, name, dose, taken_at, status, comment = row
    when = utc_to_moscow(taken_at)
    status_label = {"taken": "принят", "skipped": "пропущен", "cancelled": "отменён"}[status]
    dose_text = f" {dose}" if dose else ""
    comment_text = f"\nКомментарий: {comment}" if comment else ""
    return f"💊 {name}{dose_text} — {status_label} {when:%d.%m.%Y в %H:%M} MSK.{comment_text}"


async def start_medication_intake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show personalized one-tap medication buttons."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Какое лекарство вы приняли?",
        reply_markup=_intake_keyboard(_user_id(update)),
    )
    return "intake_choice"


async def intake_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record a quick medication or start arbitrary-medication input."""
    query = update.callback_query
    await query.answer()
    if query.data == "med_cancel":
        await query.edit_message_text(
            "Запись приёма отменена.", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        return ConversationHandler.END
    if query.data == "med_other":
        context.user_data["medication_draft"] = {}
        await query.edit_message_text("Введите название лекарства:")
        return "intake_name"

    medication_id = int(query.data.split(":", 1)[1])
    user_id = _user_id(update)
    medication = repo.get_owned(user_id, medication_id)
    if medication is None:
        await query.edit_message_text(
            "Лекарство не найдено.", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        return ConversationHandler.END
    _, name, dose, _schedule, _quick = medication
    intake_id = repo.record_intake(
        user_id, medication_id=medication_id, medication_name=name, dose=dose,
    )
    row = repo.get_owned_intake(user_id, intake_id)
    await query.edit_message_text(_format_intake(row), reply_markup=_receipt_keyboard(intake_id))
    return ConversationHandler.END


async def arbitrary_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store a one-off medication name and request its dose."""
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Название не может быть пустым.")
        return "intake_name"
    context.user_data["medication_draft"] = {"name": name}
    await update.message.reply_text(
        "Введите дозировку, например «200 мг», или нажмите «Пропустить».",
        reply_markup=ReplyKeyboardMarkup([[SKIP_TEXT], *CANCEL_KEYBOARD], resize_keyboard=True),
    )
    return "intake_dose"


async def arbitrary_dose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record a one-off medication intake."""
    draft = context.user_data.pop("medication_draft", {})
    dose = None if update.message.text == SKIP_TEXT else update.message.text.strip()
    user_id = _user_id(update)
    intake_id = repo.record_intake(
        user_id, medication_name=draft["name"], dose=dose,
    )
    row = repo.get_owned_intake(user_id, intake_id)
    await update.message.reply_text(_format_intake(row), reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        "Что сделать с записью?",
        reply_markup=_receipt_keyboard(intake_id, can_save=True),
    )
    return ConversationHandler.END


async def cancel_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any medication text-input flow."""
    context.user_data.pop("medication_draft", None)
    context.user_data.pop("medication_edit_intake", None)
    await update.message.reply_text("Действие отменено.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        "Главное меню:", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


async def medication_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return from an intake receipt to the main menu."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Главное меню:", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


async def undo_intake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Soft-cancel an intake so history remains auditable."""
    await update.callback_query.answer()
    intake_id = int(update.callback_query.data.split(":", 1)[1])
    changed = repo.update_intake(_user_id(update), intake_id, status="cancelled")
    text = "Запись приёма отменена." if changed else "Запись не найдена."
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


async def start_edit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request a corrected Moscow intake time."""
    await update.callback_query.answer()
    intake_id = int(update.callback_query.data.split(":", 1)[1])
    context.user_data["medication_edit_intake"] = intake_id
    await update.callback_query.edit_message_text("Введите время приёма в формате ЧЧ:ММ (MSK):")
    return "edit_intake_time"


async def edit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apply a corrected time on the intake's original Moscow date."""
    try:
        parsed_time = datetime.strptime(update.message.text.strip(), "%H:%M").time()
    except ValueError:
        await update.message.reply_text("Неверный формат. Например: 12:30")
        return "edit_intake_time"
    intake_id = context.user_data["medication_edit_intake"]
    user_id = _user_id(update)
    row = repo.get_owned_intake(user_id, intake_id)
    if row is None:
        return await cancel_text_flow(update, context)
    local_date = utc_to_moscow(row[4]).date()
    corrected = datetime.combine(local_date, parsed_time, tzinfo=MOSCOW_TZ)
    repo.update_intake(user_id, intake_id, taken_at=corrected)
    context.user_data.pop("medication_edit_intake", None)
    row = repo.get_owned_intake(user_id, intake_id)
    await update.message.reply_text(
        _format_intake(row), reply_markup=_receipt_keyboard(intake_id),
    )
    return ConversationHandler.END


async def start_edit_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request an intake comment."""
    await update.callback_query.answer()
    context.user_data["medication_edit_intake"] = int(
        update.callback_query.data.split(":", 1)[1]
    )
    await update.callback_query.edit_message_text(
        "Введите комментарий или «—», чтобы очистить его:"
    )
    return "edit_intake_comment"


async def edit_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save an intake comment."""
    intake_id = context.user_data.pop("medication_edit_intake")
    comment = "" if update.message.text == "—" else update.message.text
    user_id = _user_id(update)
    repo.update_intake(user_id, intake_id, comment=comment)
    row = repo.get_owned_intake(user_id, intake_id)
    await update.message.reply_text(
        _format_intake(row), reply_markup=_receipt_keyboard(intake_id),
    )
    return ConversationHandler.END


async def save_one_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Turn a one-off intake into a reusable quick-access medication."""
    await update.callback_query.answer()
    intake_id = int(update.callback_query.data.split(":", 1)[1])
    user_id = _user_id(update)
    intake = repo.get_owned_intake(user_id, intake_id)
    if intake is None:
        await update.callback_query.edit_message_text("Запись не найдена.")
        return ConversationHandler.END
    try:
        medication_id = repo.add_medication(
            user_id, name=intake[2], default_dose=intake[3], is_quick_access=True,
        )
    except sqlite3.IntegrityError:
        await update.callback_query.edit_message_text(
            "Такое лекарство уже есть в настройках.",
            reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        return ConversationHandler.END
    repo.update_intake(user_id, intake_id, medication_id=medication_id)
    await update.callback_query.edit_message_text(
        "Лекарство добавлено в быстрые кнопки.",
        reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END


def _settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for medication_id, name, dose, schedule, quick in repo.list_active(user_id):
        details = f"{name} {dose or ''}".strip()
        mode = "быстрая" if quick else "скрыта"
        rows.append([InlineKeyboardButton(
            f"{details} · {mode}", callback_data=f"med_toggle:{medication_id}",
        ), InlineKeyboardButton("Удалить", callback_data=f"med_archive:{medication_id}")])
    rows.extend([
        [InlineKeyboardButton("Добавить лекарство", callback_data="med_add")],
        [InlineKeyboardButton("Главное меню", callback_data="med_settings_done")],
    ])
    return InlineKeyboardMarkup(rows)


async def start_medication_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's medication catalogue."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "Ваши лекарства. Нажатие на лекарство включает или скрывает быструю кнопку.",
        reply_markup=_settings_keyboard(_user_id(update)),
    )
    return "settings_menu"


async def settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle catalogue toggles, archive and add actions."""
    query = update.callback_query
    await query.answer()
    user_id = _user_id(update)
    if query.data == "med_settings_done":
        await query.edit_message_text("Главное меню:", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD))
        return ConversationHandler.END
    if query.data == "med_add":
        context.user_data["medication_draft"] = {}
        await query.edit_message_text("Введите название лекарства:")
        return "settings_name"
    action, raw_id = query.data.split(":", 1)
    medication = repo.get_owned(user_id, int(raw_id))
    if medication:
        if action == "med_toggle":
            repo.set_quick_access(user_id, medication[0], not bool(medication[4]))
        elif action == "med_archive":
            repo.archive(user_id, medication[0])
    await query.edit_message_text(
        "Настройки лекарств обновлены.", reply_markup=_settings_keyboard(user_id),
    )
    return "settings_menu"


async def settings_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect a reusable medication name."""
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Название не может быть пустым.")
        return "settings_name"
    context.user_data["medication_draft"] = {"name": name}
    await update.message.reply_text(
        "Введите обычную дозировку или нажмите «Пропустить».",
        reply_markup=ReplyKeyboardMarkup([[SKIP_TEXT], *CANCEL_KEYBOARD], resize_keyboard=True),
    )
    return "settings_dose"


async def settings_dose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect the default dose and ask whether use is daily."""
    context.user_data["medication_draft"]["dose"] = (
        None if update.message.text == SKIP_TEXT else update.message.text.strip()
    )
    await update.message.reply_text(
        "Как принимается лекарство?",
        reply_markup=ReplyKeyboardMarkup(
            [["Ежедневно", "По необходимости"], ["Отмена"]], resize_keyboard=True,
        ),
    )
    return "settings_schedule"


async def settings_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a reusable quick-access medication."""
    schedules = {"Ежедневно": "daily", "По необходимости": "as_needed"}
    if update.message.text not in schedules:
        await update.message.reply_text("Выберите вариант на клавиатуре.")
        return "settings_schedule"
    draft = context.user_data.pop("medication_draft")
    try:
        repo.add_medication(
            _user_id(update), name=draft["name"], default_dose=draft["dose"],
            schedule_type=schedules[update.message.text], is_quick_access=True,
        )
    except sqlite3.IntegrityError:
        await update.message.reply_text(
            "Лекарство с таким названием уже существует.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "Главное меню:", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
        )
        return ConversationHandler.END
    await update.message.reply_text("Лекарство добавлено.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        "Главное меню:", reply_markup=InlineKeyboardMarkup(WLCOME_KEYBOARD),
    )
    return ConversationHandler.END
