from enum import Enum
from telegram import InlineKeyboardButton


WLCOME_KEYBOARD = [
    ["Записать результат измерения", "Посмотреть последний результат"]
]


class BodyPosition(Enum):
    STANDING = 1
    SITTING = 2
    RECLINING = 3
    LYING = 4
    NOT_SET = 5


class ArmLocation(Enum):
    LEFT_WRIST = 1
    RIGTH_WRIST = 2
    LEFT_UPPER_ARM = 3
    RIGTH_UPPER_ARM = 4
    NOT_SET = 5


BODY_POSITION_KEYBOARD = [
    [InlineKeyboardButton("Стоя", callback_data=BodyPosition.STANDING)],
    [InlineKeyboardButton("Сидя", callback_data=BodyPosition.SITTING)],
    [InlineKeyboardButton("Лёжа", callback_data=BodyPosition.RECLINING)],
    [InlineKeyboardButton("Полу лёжа", callback_data=BodyPosition.LYING)],
    [InlineKeyboardButton("Не указано", callback_data=BodyPosition.NOT_SET)],
]


ARM_LOCATION_KEYBOARD = [
    [InlineKeyboardButton("Левая рука", callback_data=ArmLocation.LEFT_WRIST)],
    [InlineKeyboardButton("Правая рука", callback_data=ArmLocation.RIGTH_WRIST)],
    [InlineKeyboardButton("Левое плечё", callback_data=ArmLocation.LEFT_UPPER_ARM)],
    [InlineKeyboardButton("Правое плечё", callback_data=ArmLocation.RIGTH_UPPER_ARM)],
    [InlineKeyboardButton("Не указано", callback_data=ArmLocation.NOT_SET)],
]
