from enum import Enum


class RoleType(Enum):
    ASSISTANT = "assistant"
    USER = "user"
    DEFAULT = "default"


class ModeType(Enum):
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_32k = "gpt-4-32k"


class TaskType(Enum):
    AI_SOCIETY = "ai_society"
    CODE = "code"
    MISALIGNMENT = "misalignment"
    DEFAULT = "default"


__all__ = ['RoleType', 'ModeType', 'TaskType']
