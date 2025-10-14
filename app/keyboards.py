"""./app/keyboards.py
Static keyboard layouts for Telegram reply keyboards."""
from telegram import InlineKeyboardButton


WLCOME_KEYBOARD = [
    [InlineKeyboardButton('Записать результат измерения', callback_data='add_measurement')],
    [InlineKeyboardButton('Посмотреть последний результат', callback_data='last_measurement')],
    [InlineKeyboardButton('Сводка за период', callback_data='get_day_statistics')]
]

WITH_EDIT_BUTTON_KEYBOARD = [
    [InlineKeyboardButton('Записать результат измерения', callback_data='add_measurement')],
    [InlineKeyboardButton('Изменить последний результат', callback_data='edit_last_measurement')],
    [InlineKeyboardButton('Сводка за период', callback_data='get_day_statistics')]
]

BODY_POSITION_KEYBOARD = [
    ["Стоя", "Сидя", "Лёжа", "Полу лёжа", "Не указано",]
]

ARM_LOCATION_KEYBOARD = [
    ["Левая рука", "Правая рука", "Левое плечо", "Правое плечо", "Не указано",]
]

WELL_BEING_KEYBOARD = [
    ["Хорошо", "Нормально", "Плохо"]
]

EDIT_KEYBOARD = [
    [InlineKeyboardButton('Артериальное давление', callback_data='edit_pressure')],
    [InlineKeyboardButton('Пульс', callback_data='edit_pulse')],
    [InlineKeyboardButton('Положение', callback_data='edit_body_position')],
    [InlineKeyboardButton('Манжета', callback_data='edit_arm_location')],
    [InlineKeyboardButton('Самочувствие', callback_data='edit_well_being')],
    [InlineKeyboardButton('Комментарий', callback_data='edit_comment')],
    [
        InlineKeyboardButton('Сохранить', callback_data='save_edit'),
        InlineKeyboardButton('Отменить', callback_data='cancel_edit'),
    ],
]
