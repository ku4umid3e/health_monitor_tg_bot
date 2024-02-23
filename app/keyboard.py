from telegram import InlineKeyboardButton


WLCOME_KEYBOARD = [
    [
        InlineKeyboardButton("Записать результат измерения", callback_data="1"),
    ],
    [
        InlineKeyboardButton("Посмотреть последний результат", callback_data="2")
    ]
]
