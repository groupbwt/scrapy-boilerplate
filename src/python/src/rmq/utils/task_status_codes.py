from enum import IntEnum


class TaskStatusCodes(IntEnum):
    NOT_PROCESSED = 0
    IN_QUEUE = 1
    SUCCESS = 2
    PARTIAL_SUCCESS = 21
    ERROR = 4
    HARDWARE_ERROR = 41
