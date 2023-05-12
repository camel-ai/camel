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
    r"""Base class for message objects used in CAMEL chat system.

    Args:
        role_name (str): The name of the user or assistant role.
        role_type (RoleType): The type of role, either
            :obj:`RoleType.ASSISTANT` or :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system, either
            :obj:`"system"`, :obj:`"user"`, or :obj:`"assistant"`.
        content (str): The content of the message.
    """
    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]]
    role: str
    content: str

    def to_user_chat_message(self) -> "UserChatMessage":
        r"""Converts the message to a :obj:`UserChatMessage` object.

        Returns:
            UserChatMessage: The converted :obj:`UserChatMessage` object.
        """
        return UserChatMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=self.meta_dict,
            content=self.content,
        )

    def to_assistant_chat_message(self) -> "AssistantChatMessage":
        r"""Converts the message to an :obj:`AssistantChatMessage` object.

        Returns:
            AssistantChatMessage: The converted :obj:`AssistantChatMessage`
                object.
        """
        return AssistantChatMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=self.meta_dict,
            content=self.content,
        )

    def to_openai_message(self, role: Optional[str] = None) -> OpenAIMessage:
        r"""Converts the message to an :obj:`OpenAIMessage` object.

        Args:
            role (Optional[str]): The role of the message in OpenAI chat
                system, either :obj:`"system"`, :obj:`"user"`, or
                obj:`"assistant"`. (default: :obj:`None`)

        Returns:
            OpenAIMessage: The converted :obj:`OpenAIMessage` object.
        """
        role = role or self.role
        if role not in {"system", "user", "assistant"}:
            raise ValueError(f"Unrecognized role: {role}")
        return {"role": role, "content": self.content}

    def to_openai_chat_message(
        self,
        role: Optional[str] = None,
    ) -> OpenAIChatMessage:
        r"""Converts the message to an :obj:`OpenAIChatMessage` object.

        Args:
            role (Optional[str]): The role of the message in OpenAI chat
                system, either :obj:`"user"`, or :obj:`"assistant"`.
                (default: :obj:`None`)

        Returns:
            OpenAIChatMessage: The converted :obj:`OpenAIChatMessage` object.
        """
        role = role or self.role
        if role not in {"user", "assistant"}:
            raise ValueError(f"Unrecognized role: {role}")
        return {"role": role, "content": self.content}

    def to_openai_system_message(self) -> OpenAISystemMessage:
        r"""Converts the message to an :obj:`OpenAISystemMessage` object.

        Returns:
            OpenAISystemMessage: The converted :obj:`OpenAISystemMessage`
                object.
        """
        return {"role": "system", "content": self.content}

    def to_openai_user_message(self) -> OpenAIUserMessage:
        r"""Converts the message to an :obj:`OpenAIUserMessage` object.

        Returns:
            OpenAIUserMessage: The converted :obj:`OpenAIUserMessage` object.
        """
        return {"role": "user", "content": self.content}

    def to_openai_assistant_message(self) -> OpenAIAssistantMessage:
        r"""Converts the message to an :obj:`OpenAIAssistantMessage` object.

        Returns:
            OpenAIAssistantMessage: The converted :obj:`OpenAIAssistantMessage`
                object.
        """
        return {"role": "assistant", "content": self.content}

    def to_dict(self) -> Dict:
        r"""Converts the message to a dictionary.

        Returns:
            dict: The converted dictionary.
        """
        return {
            "role_name": self.role_name,
            "role_type": self.role_type.name,
            **(self.meta_dict or {}),
            "role": self.role,
            "content": self.content,
        }


@dataclass
class SystemMessage(BaseMessage):
    r"""Class for system messages used in CAMEL chat system.

    Args:
        role_name (str): The name of the user or assistant role.
        role_type (RoleType): The type of role, either
            :obj:`RoleType.ASSISTANT` or :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system.
            (default: :obj:`"system"`)
        content (str): The content of the message. (default: :obj:`""`)
    """
    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "system"
    content: str = ""


@dataclass
class AssistantSystemMessage(SystemMessage):
    r"""Class for system messages from the assistant used in the CAMEL chat
    system.

    Args:
        role_name (str): The name of the assistant role.
        role_type (RoleType): The type of role, always
            :obj:`RoleType.ASSISTANT`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system.
            (default: :obj:`"system"`)
        content (str): The content of the message. (default: :obj:`""`)
    """
    role_name: str
    role_type: RoleType = RoleType.ASSISTANT
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "system"
    content: str = ""


@dataclass
class UserSystemMessage(SystemMessage):
    r"""Class for system messages from the user used in the CAMEL chat system.

    Args:
        role_name (str): The name of the user role.
        role_type (RoleType): The type of role, always :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system.
            (default: :obj:`"system"`)
        content (str): The content of the message. (default: :obj:`""`)
    """
    role_name: str
    role_type: RoleType = RoleType.USER
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "system"
    content: str = ""


@dataclass
class ChatMessage(BaseMessage):
    r"""Base class for chat messages used in CAMEL chat system.

    Args:
        role_name (str): The name of the user or assistant role.
        role_type (RoleType): The type of role, either
            :obj:`RoleType.ASSISTANT` or :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system.
        content (str): The content of the message. (default: :obj:`""`)
    """
    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]]
    role: str
    content: str = ""


@dataclass
class AssistantChatMessage(ChatMessage):
    r"""Class for chat messages from the assistant role used in CAMEL chat
    system.

    Args:
        role_name (str): The name of the assistant role.
        role_type (RoleType): The type of role, always
            :obj:`RoleType.ASSISTANT`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system.
            (default: :obj:`"assistant"`)
        content (str): The content of the message. (default: :obj:`""`)
    """
    role_name: str
    role_type: RoleType = RoleType.ASSISTANT
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "assistant"
    content: str = ""


@dataclass
class UserChatMessage(ChatMessage):
    r"""Class for chat messages from the user role used in CAMEL chat system.

    Args:
        role_name (str): The name of the user role.
        role_type (RoleType): The type of role, always :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        role (str): The role of the message in OpenAI chat system.
            (default: :obj:`"user"`)
        content (str): The content of the message. (default: :obj:`""`)
    """
    role_name: str
    role_type: RoleType = RoleType.USER
    meta_dict: Optional[Dict[str, str]] = None
    role: str = "user"
    content: str = ""


MessageType = Union[BaseMessage, SystemMessage, AssistantSystemMessage,
                    UserSystemMessage, ChatMessage, AssistantChatMessage,
                    UserChatMessage]
SystemMessageType = Union[SystemMessage, AssistantSystemMessage,
                          UserSystemMessage]
ChatMessageType = Union[ChatMessage, AssistantChatMessage, UserChatMessage]
