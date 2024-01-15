from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard():
    return ReplyKeyboardMarkup([
        ["Записать измерения"],
        ["Показать измерения"],
    ], resize_keyboard=True
    )
