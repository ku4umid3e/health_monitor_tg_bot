from enum import Enum


class BodyPosition(Enum):
    STANDING = "1"
    SITTING = "2"
    RECLINING = "3"
    LYING = "4"
    NOT_SET = "5"


class ArmLocation(Enum):
    LEFT_WRIST = 1
    RIGTH_WRIST = 2
    LEFT_UPPER_ARM = 3
    RIGTH_UPPER_ARM = 4
    NOT_SET = 5
