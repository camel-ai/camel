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
            "role_type": self.role_type.name,
            "role_name": self.role_name,
            "role": self.role,
            "content": self.content,
        }


@dataclass
class CodeBaseMessage:
    language_name: str
    domain_name: str
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
            "language_name": self.language_name,
            "domain_name": self.domain_name,
            "role": self.role,
            "content": self.content,
        }


@dataclass
class GenericBaseMessage:
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
        meta_dict = self.meta_dict.copy()
        meta_dict.update({
            "role_type": self.role_type.name,
            "role": self.role,
            "content": self.content,
        })
        return meta_dict


@dataclass
class GenericMessage(GenericBaseMessage):
    meta_dict: dict
    role_type: RoleType
    role: str
    content: str = ""


@dataclass
class GenericChatMessage(GenericBaseMessage):
    meta_dict: dict
    role_type: RoleType
    role: str
    content: str = ""


@dataclass
class SystemMessage(BaseMessage):
    role_name: str
    role_type: RoleType
    role: str = "system"
    content: str = ""


@dataclass
class AssistantSystemMessage(SystemMessage):
    role_name: str
    role_type: RoleType = RoleType.ASSISTANT
    role: str = "system"
    content: str = ""


@dataclass
class UserSystemMessage(SystemMessage):
    role_name: str
    role_type: RoleType = RoleType.USER
    role: str = "system"
    content: str = ""


@dataclass
class ChatMessage(BaseMessage):
    role_name: str
    role_type: RoleType
    role: str
    content: str = ""


@dataclass
class AssistantChatMessage(ChatMessage):
    role_name: str
    role_type: RoleType = RoleType.ASSISTANT
    role: str = "assistant"
    content: str = ""


@dataclass
class UserChatMessage(ChatMessage):
    role_name: str
    role_type: RoleType = RoleType.USER
    role: str = "user"
    content: str = ""


@dataclass
class CodeSystemMessage(CodeBaseMessage):
    language_name: str
    domain_name: str
    role_type: RoleType
    role: str = "system"
    content: str = ""


@dataclass
class CodeAssistantSystemMessage(CodeSystemMessage):
    language_name: str
    domain_name: str
    role_type: RoleType = RoleType.ASSISTANT
    role: str = "system"
    content: str = ""


@dataclass
class CodeUserSystemMessage(CodeSystemMessage):
    language_name: str
    domain_name: str
    role_type: RoleType = RoleType.USER
    role: str = "system"
    content: str = ""


MessageType = Union[BaseMessage, SystemMessage, AssistantSystemMessage,
                    UserSystemMessage, ChatMessage, AssistantChatMessage,
                    UserChatMessage, CodeSystemMessage,
                    CodeAssistantSystemMessage, CodeUserSystemMessage]
SystemMessageType = Union[SystemMessage, AssistantSystemMessage,
                          UserSystemMessage, CodeSystemMessage,
                          CodeAssistantSystemMessage, CodeUserSystemMessage]
ChatMessageType = Union[ChatMessage, AssistantChatMessage, UserChatMessage]
