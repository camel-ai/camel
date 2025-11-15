import json
from typing import Literal, Optional

from pydantic import BaseModel, Field

from tau2.utils.utils import get_now

SystemRole = Literal["system"]
UserRole = Literal["user"]
AssistantRole = Literal["assistant"]
ToolRole = Literal["tool"]
ToolRequestor = Literal["user", "assistant"]


class SystemMessage(BaseModel):
    """
    A system message.
    """

    role: SystemRole = Field(description="The role of the message sender.")
    content: Optional[str] = Field(
        description="The content of the message.", default=None
    )
    turn_idx: Optional[int] = Field(
        description="The index of the turn in the conversation.", default=None
    )
    timestamp: Optional[str] = Field(
        description="The timestamp of the message.", default_factory=get_now
    )

    def __str__(self) -> str:
        lines = [
            "SystemMessage",
        ]
        if self.turn_idx is not None:
            lines.append(f"turn_idx: {self.turn_idx}")
        if self.timestamp is not None:
            lines.append(f"timestamp: {self.timestamp}")
        if self.content is not None:
            lines.append(f"content: {self.content}")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SystemMessage):
            return False
        return self.role == other.role and self.content == other.content


class ToolCall(BaseModel):
    """
    A tool call.
    """

    id: str = Field(default="", description="The unique identifier for the tool call.")
    name: str = Field(description="The name of the tool.")
    arguments: dict = Field(description="The arguments of the tool.")
    requestor: ToolRequestor = Field(
        "assistant",
        description="The requestor of the tool call.",
    )

    def __str__(self) -> str:
        lines = [f"ToolCall (from {self.requestor})"]
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"name: {self.name}")
        lines.append(f"arguments:\n{json.dumps(self.arguments, indent=2)}")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ToolCall):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.arguments == other.arguments
            and self.requestor == other.requestor
        )


class ParticipantMessageBase(BaseModel):
    """
    A message from a participant in the conversation.
    if content is None, then tool_calls must be provided
    if tool_calls is None, then content must be provided
    """

    role: str = Field(description="The role of the message sender.")

    content: Optional[str] = Field(
        description="The content of the message.", default=None
    )
    tool_calls: Optional[list[ToolCall]] = Field(
        description="The tool calls made in the message.", default=None
    )
    turn_idx: Optional[int] = Field(
        description="The index of the turn in the conversation.", default=None
    )
    timestamp: Optional[str] = Field(
        description="The timestamp of the message.", default_factory=get_now
    )
    cost: Optional[float] = Field(description="The cost of the message.", default=None)

    usage: Optional[dict] = Field(
        description="The token usage of the message.", default=None
    )
    raw_data: Optional[dict] = Field(
        description="The raw data of the message.", default=None
    )

    def validate(self):  # NOTE: It would be better to do this in the Pydantic model
        """
        Validate the message.
        """
        if not (self.has_text_content() or self.is_tool_call()):
            raise ValueError(
                f"AssistantMessage must have either content or tool calls. Got {self}"
            )

    def has_text_content(self) -> bool:
        """
        Check if the message has text content.
        """
        if self.content is None:
            return False
        if isinstance(self.content, str) and self.content.strip() == "":
            return False
        return True

    def is_tool_call(self) -> bool:
        """
        Check if the message is a tool call.
        """
        return self.tool_calls is not None

    def __str__(self) -> str:
        lines = [f"{self.role.capitalize()}Message"]
        if self.turn_idx is not None:
            lines.append(f"turn_idx: {self.turn_idx}")
        if self.timestamp is not None:
            lines.append(f"timestamp: {self.timestamp}")
        if self.content is not None:
            lines.append(f"content: {self.content}")
        if self.tool_calls is not None:
            lines.append("ToolCalls")
            lines.extend([str(tool_call) for tool_call in self.tool_calls])
        if self.cost is not None:
            lines.append(f"cost: {self.cost}")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return (
            self.role == other.role
            and self.content == other.content
            and self.tool_calls == other.tool_calls
        )


class AssistantMessage(ParticipantMessageBase):
    """
    A message from the assistant
    """

    role: AssistantRole = Field(description="The role of the message sender.")


class UserMessage(ParticipantMessageBase):
    """
    A message from the user.
    """

    role: UserRole = Field(description="The role of the message sender.")


class ToolMessage(BaseModel):
    """
    A message from the tool.
    """

    id: str = Field(description="The unique identifier for the tool call.")
    role: ToolRole = Field(description="The role of the message sender.")
    content: Optional[str] = Field(description="The output of the tool.", default=None)
    requestor: Literal["user", "assistant"] = Field(
        "assistant",
        description="The requestor of the tool call.",
    )
    error: bool = Field(description="Whether the tool call failed.", default=False)
    turn_idx: Optional[int] = Field(
        description="The index of the turn in the conversation.", default=None
    )
    timestamp: Optional[str] = Field(
        description="The timestamp of the message.", default_factory=get_now
    )

    def __str__(self) -> str:
        lines = [f"ToolMessage (responding to {self.requestor})"]
        if self.turn_idx is not None:
            lines.append(f"turn_idx: {self.turn_idx}")
        if self.timestamp is not None:
            lines.append(f"timestamp: {self.timestamp}")
        if self.content is not None:
            lines.append(f"content: {self.content}")
        if self.error:
            lines.append("Error")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return (
            self.id == other.id
            and self.role == other.role
            and self.content == other.content
            and self.requestor == other.requestor
            and self.error == other.error
        )


class MultiToolMessage(BaseModel):
    """
    Encapsulates multiple tool messages.
    """

    role: ToolRole = Field(description="The role of the message sender.")
    tool_messages: list[ToolMessage] = Field(description="The tool messages.")


APICompatibleMessage = SystemMessage | AssistantMessage | UserMessage | ToolMessage
Message = (
    SystemMessage | AssistantMessage | UserMessage | ToolMessage | MultiToolMessage
)
