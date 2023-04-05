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
    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]]
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
            "role_name": self.role_name,
            "role_type": self.role_type.name,
            **(self.meta_dict or {}),
            "role": self.role,
            "content": self.content,
        }


@dataclass
class SystemMessage(BaseMessage):
    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "system"
    content: str = ""


@dataclass
class AssistantSystemMessage(SystemMessage):
    role_name: str
    role_type: RoleType = RoleType.ASSISTANT
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "system"
    content: str = ""


@dataclass
class UserSystemMessage(SystemMessage):
    role_name: str
    role_type: RoleType = RoleType.USER
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "system"
    content: str = ""


@dataclass
class ChatMessage(BaseMessage):
    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]]
    role: str
    content: str = ""


@dataclass
class AssistantChatMessage(ChatMessage):
    role_name: str
    role_type: RoleType = RoleType.ASSISTANT
    meta_dict: Dict[str, str] = None
    role: str = "assistant"
    content: str = ""


@dataclass
class UserChatMessage(ChatMessage):
    role_name: str
    role_type: RoleType = RoleType.USER
    meta_dict: Dict[str, str] = None
    role: str = "user"
    content: str = ""


MessageType = Union[BaseMessage, SystemMessage, AssistantSystemMessage,
                    UserSystemMessage, ChatMessage, AssistantChatMessage,
                    UserChatMessage]
SystemMessageType = Union[SystemMessage, AssistantSystemMessage,
                          UserSystemMessage]
ChatMessageType = Union[ChatMessage, AssistantChatMessage, UserChatMessage]
