"""./app/keyboards.py
Static keyboard layouts for Telegram reply keyboards."""
from telegram import InlineKeyboardButton


CANCEL_TEXT = "Отмена"
SKIP_TEXT = "Пропустить"

WLCOME_KEYBOARD = [
    [InlineKeyboardButton('Записать результат измерения', callback_data='add_measurement')],
    [InlineKeyboardButton('Посмотреть последний результат', callback_data='last_measurement')],
    [InlineKeyboardButton('Сводка за период', callback_data='get_day_statistics')]
]

STATISTICS_PERIOD_KEYBOARD = [[
    InlineKeyboardButton('За неделю', callback_data='statistics_week'),
    InlineKeyboardButton('За месяц', callback_data='statistics_month'),
], [
    InlineKeyboardButton('Назад', callback_data='statistics_back'),
]]

WITH_EDIT_BUTTON_KEYBOARD = [
    [InlineKeyboardButton('Записать результат измерения', callback_data='add_measurement')],
    [InlineKeyboardButton('Изменить последний результат', callback_data='edit_last_measurement')],
    [InlineKeyboardButton('Сводка за период', callback_data='get_day_statistics')]
]

BODY_POSITION_KEYBOARD = [
    ["Стоя", "Сидя", "Лёжа", "Полу-лёжа", "Не указано"],
    [CANCEL_TEXT],
]

ARM_LOCATION_KEYBOARD = [
    ["Левая рука", "Правая рука", "Левое плечо", "Правое плечо", "Не указано"],
    [CANCEL_TEXT],
]

WELL_BEING_KEYBOARD = [
    ["Хорошо", "Нормально", "Плохо"],
    [CANCEL_TEXT],
]

CANCEL_KEYBOARD = [[CANCEL_TEXT]]
COMMENT_KEYBOARD = [[SKIP_TEXT], [CANCEL_TEXT]]

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

EDIT_BODY_POSITION_KEYBOARD = [[
    InlineKeyboardButton('Стоя', callback_data='set_body_position:1'),
    InlineKeyboardButton('Сидя', callback_data='set_body_position:2'),
], [
    InlineKeyboardButton('Лёжа', callback_data='set_body_position:3'),
    InlineKeyboardButton('Полу-лёжа', callback_data='set_body_position:4'),
], [
    InlineKeyboardButton('Не указано', callback_data='set_body_position:5'),
]]

EDIT_ARM_LOCATION_KEYBOARD = [[
    InlineKeyboardButton('Левая рука', callback_data='set_arm_location:1'),
    InlineKeyboardButton('Правая рука', callback_data='set_arm_location:2'),
], [
    InlineKeyboardButton('Левое плечо', callback_data='set_arm_location:3'),
    InlineKeyboardButton('Правое плечо', callback_data='set_arm_location:4'),
], [
    InlineKeyboardButton('Не указано', callback_data='set_arm_location:5'),
]]

EDIT_WELL_BEING_KEYBOARD = [[
    InlineKeyboardButton('Хорошо', callback_data='set_well_being:1'),
    InlineKeyboardButton('Нормально', callback_data='set_well_being:2'),
    InlineKeyboardButton('Плохо', callback_data='set_well_being:3'),
]]
