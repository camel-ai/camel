from dataclasses import dataclass
from typing import Dict, Optional, Union

from .typing import RoleType

OpenAISystemMessage = Dict[str, str]
OpenAIAssistantMessage = Dict[str, str]
OpenAIUserMessage = Dict[str, str]
OpenAIChatMessage = Union[OpenAIUserMessage, OpenAIAssistantMessage]
OpenAIMessage = Union[OpenAISystemMessage, OpenAIChatMessage]


@dataclass
class BaseMessage:
    meta_dict: Dict[str, str]
    role_type: RoleType
    role: str
    content: str

    def to_openai_message(self, role: Optional[str] = None) -> OpenAIMessage:
        role = role or self.role
        assert role in ["system", "user", "assistant"]
        return {"role": role, "content": self.content}

    def to_openai_chat_message(
        self,
        role: Optional[str] = None,
    ) -> OpenAIChatMessage:
        role = role or self.role
        assert role in ["user", "assistant"]
        return {"role": role, "content": self.content}

    def to_openai_system_message(self) -> OpenAISystemMessage:
        return {"role": "system", "content": self.content}

    def to_openai_user_message(self) -> OpenAIUserMessage:
        return {"role": "user", "content": self.content}

    def to_openai_assistant_message(self) -> OpenAIAssistantMessage:
        return {"role": "assistant", "content": self.content}

    def to_dict(self) -> Dict:
        return {
            **self.meta_dict,
            "role_type": self.role_type.name,
            "role": self.role,
            "content": self.content,
        }


@dataclass
class SystemMessage(BaseMessage):
    meta_dict: Dict[str, str]
    role_type: RoleType
    role: str = "system"
    content: str = ""


@dataclass
class AssistantSystemMessage(SystemMessage):
    meta_dict: Dict[str, str]
    role_type: RoleType = RoleType.ASSISTANT
    role: str = "system"
    content: str = ""


@dataclass
class UserSystemMessage(SystemMessage):
    meta_dict: Dict[str, str]
    role_type: RoleType = RoleType.USER
    role: str = "system"
    content: str = ""


@dataclass
class ChatMessage(BaseMessage):
    meta_dict: Dict[str, str]
    role_type: RoleType
    role: str
    content: str = ""


@dataclass
class AssistantChatMessage(ChatMessage):
    meta_dict: Dict[str, str]
    role_type: RoleType = RoleType.ASSISTANT
    role: str = "assistant"
    content: str = ""


@dataclass
class UserChatMessage(ChatMessage):
    meta_dict: Dict[str, str]
    role_type: RoleType = RoleType.USER
    role: str = "user"
    content: str = ""


MessageType = Union[BaseMessage, SystemMessage, AssistantSystemMessage,
                    UserSystemMessage, ChatMessage, AssistantChatMessage,
                    UserChatMessage]
SystemMessageType = Union[SystemMessage, AssistantSystemMessage,
                          UserSystemMessage]
ChatMessageType = Union[ChatMessage, AssistantChatMessage, UserChatMessage]
