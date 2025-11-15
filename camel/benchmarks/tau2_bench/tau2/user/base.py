from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional

from loguru import logger
from pydantic import BaseModel

from tau2.data_model.message import (
    APICompatibleMessage,
    AssistantMessage,
    Message,
    MultiToolMessage,
    SystemMessage,
    ToolMessage,
    UserMessage,
)

ValidUserInputMessage = UserMessage | ToolMessage | MultiToolMessage


class UserError(Exception):
    """
    Generic exception for user errors.
    """

    pass


def is_valid_user_history_message(message: Message) -> bool:
    """Check if the message is a valid user history message."""
    return (
        isinstance(message, UserMessage)
        or (isinstance(message, AssistantMessage) and not message.is_tool_call())
        or (isinstance(message, ToolMessage) and message.requestor == "user")
    )


STOP = "###STOP###"
TRANSFER = "###TRANSFER###"
OUT_OF_SCOPE = "###OUT-OF-SCOPE###"


class UserState(BaseModel):
    """The state of the user simulator."""

    system_messages: list[SystemMessage]
    messages: list[APICompatibleMessage]

    def flip_roles(self) -> list[APICompatibleMessage]:
        """
        Returns a list of messages with the roles flipped.
        """
        # NOTE: also clean the message to a api-compatible format
        flipped_messages = []
        for message in self.messages:
            if isinstance(message, UserMessage):
                flipped_messages.append(
                    AssistantMessage(
                        role="assistant",
                        tool_calls=message.tool_calls,
                        content=message.content,
                    )
                )
            elif isinstance(message, AssistantMessage):
                if not message.is_tool_call():
                    # Only add non tool call messages
                    flipped_messages.append(
                        UserMessage(
                            role="user",
                            content=message.content,
                        )
                    )
                else:
                    raise ValueError(
                        f"Tool calls are not supported in the flipped messages: {message}"
                    )
            elif isinstance(message, ToolMessage):
                if message.requestor == "user":
                    # Only add tool messages for the user
                    flipped_messages.append(
                        ToolMessage(
                            id=message.id,
                            role=message.role,
                            content=message.content,
                        )
                    )
                else:
                    raise ValueError(
                        f"Tool messages should be sent to the user in this message history: {message}"
                    )
            else:
                print(message, type(message))
                raise ValueError(f"Unknown message role: {message.role}")
        return flipped_messages


class BaseUser(ABC):
    """The base class for a user simulator."""

    def __init__(
        self,
        instructions: Optional[str] = None,
        llm: Optional[str] = None,
        llm_args: Optional[dict] = None,
    ):
        self.llm = llm
        self.llm_args = deepcopy(llm_args) if llm_args is not None else {}
        self.instructions = instructions

    @abstractmethod
    async def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> UserState:
        """Get the initial state of the user simulator.

        Args:
            message_history: The message history of the conversation.

        Returns:
            The initial state of the user simulator.
        """
        pass

    @abstractmethod
    async def generate_next_message(
        self, message: ValidUserInputMessage, state: UserState
    ) -> tuple[UserMessage, UserState]:
        """Generate the next message from an assistant message.

        Args:
            message: The agent message.
            state: The state of the user simulator.

        Returns:
            A tuple containing the user message and the new state of the user simulator.
        """
        pass

    @classmethod
    @abstractmethod
    def is_stop(cls, message: UserMessage) -> bool:
        """Check if the user message is a stop message.

        Args:
            message: The user message.

        Returns:
            True if the user message is a stop message, False otherwise.
        """
        pass

    def set_seed(self, seed: int):
        if self.llm is None:
            raise ValueError("LLM is not set")
        cur_seed = self.llm_args.get("seed", None)
        if cur_seed is not None:
            logger.warning(f"Seed is already set to {cur_seed}, resetting it to {seed}")
        self.llm_args["seed"] = seed

    def stop(
        self, message: Optional[UserMessage] = None, state: Optional[UserState] = None
    ) -> None:
        """
        Stops the user simulator.
        """
        pass
