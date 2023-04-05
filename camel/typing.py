from enum import Enum


class RoleType(Enum):
    ASSISTANT = "assistant"
    USER = "user"
    DEFAULT = "default"


class ModeType(Enum):
    GPT_3_5_TURBO = "gpt-3.5-turbo"


class TaskType(Enum):
    AI_SOCIETY = "ai_society"
    CODE = "code"
    MISALIGNMENT = "misalignment"
    DEFAULT = "default"


__all__ = ['RoleType', 'ModeType', 'TaskType']
