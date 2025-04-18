# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import abc
import threading
from enum import Enum
from functools import wraps
from typing import Any, Callable, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

from camel.agents import ChatAgent
from camel.messages import BaseMessage

T = TypeVar('T')


class ProgrammableAgentRequirement(Enum):
    r"""Requirements for programmable agent state.

    Defines the possible requirements that can be used to repair the state
    of a programmable agent.

    Attributes:
        LAST_MESSAGE_NOT_USER (str): Requires that the last message in the
            conversation was not from the user.
    """

    LAST_MESSAGE_NOT_USER = "LAST_MESSAGE_NOT_USER"


class ProgrammedAgentInstructionResult(BaseModel, Generic[T]):
    r"""Result of a programmable agent instruction execution.

    Contains the messages exchanged during execution and the computed value.
    The value type is specified by the generic type parameter T.

    Attributes:
        user_message (BaseMessage): The message sent by the user.
        agent_message (BaseMessage): The message sent by the agent.
        value (T): The computed result value of type T.
    """

    user_message: BaseMessage
    agent_message: BaseMessage
    value: T

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AbstractProgrammableAgent(abc.ABC):
    r"""Abstract class for a programmable agent.

    A programmable agent is an agent that can be programmed to perform a
    specific function or task. This class defines the interface for a
    programmable agent.

    These methods should be implemented in order to ensure the agent supports
    the necessary guarantees to enable a programming interface while
    maintaining compatibility in a multi-agent system.

    A programmable agent is responsible for providing and maintaining a
    programming interface for its functionality.
    """

    @abc.abstractmethod
    def run_atomic(
        self, callback: Callable[[], ProgrammedAgentInstructionResult[T]]
    ) -> ProgrammedAgentInstructionResult[T]:
        r"""Run an atomic operation on the agent.

        An atomic operation is an operation that is guaranteed to
        be executed without interruption by any other operation.

        Args:
            callback (Callable[[], ProgrammedAgentInstructionResult[T]]): The
                operation to execute atomically.

        Returns:
            ProgrammedAgentInstructionResult[T]: The result of the operation.

        Raises:
            RuntimeError: If an operation is already in progress.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def repair_state(self, requirement: ProgrammableAgentRequirement) -> None:
        r"""Repair the state of the agent.

        Agents may have other non-atomic interfaces, such as a user interface,
        or chat between other agents. This method should restore the agent to
        a state where it can perform operations according to the specified
        requirement.

        Args:
            requirement (ProgrammableAgentRequirement): The requirement to
                repair the state for.
        """
        raise NotImplementedError


def programmable_capability(
    func: Callable[..., ProgrammedAgentInstructionResult[T]],
) -> Callable[..., ProgrammedAgentInstructionResult[T]]:
    r"""Decorator for programmable agent capabilities.

    This decorator ensures that the decorated method is executed atomically
    and maintains the agent's state guarantees.

    Args:
        func (Callable[..., ProgrammedAgentInstructionResult[T]]): The method
            to decorate.

    Returns:
        Callable[..., ProgrammedAgentInstructionResult[T]]: The decorated
            method that ensures atomic execution.
    """

    @wraps(func)
    def wrapper(
        self, *args: Any, **kwargs: Any
    ) -> ProgrammedAgentInstructionResult[T]:
        return self.run_atomic(lambda: func(self, *args, **kwargs))

    return wrapper


class ProgrammableChatAgent(ChatAgent, AbstractProgrammableAgent):
    r"""A chat agent that can be programmed to perform specific tasks.

    Provides a default implementation of atomic execution using threading locks
    and basic state tracking for message roles. Implementing classes need to
    provide specific repair logic for their use cases.

    Attributes:
        _operation_lock (threading.Lock): Lock for ensuring atomic operations.
        _last_message_role (Optional[str]): Role of the last message in the
            conversation.
    """

    def __init__(self, **kwargs: Any) -> None:
        r"""Initialize the ProgrammableChatAgent.

        Args:
            **kwargs (Any): Additional keyword arguments to pass to parent
                class.
        """
        super().__init__(**kwargs)
        self._operation_lock = threading.Lock()
        self._last_message_role: Optional[str] = None

    def run_atomic(
        self, callback: Callable[[], ProgrammedAgentInstructionResult[T]]
    ) -> ProgrammedAgentInstructionResult[T]:
        r"""Run an atomic operation on the agent.

        Ensures thread-safe execution of the callback function by using a lock.

        Args:
            callback (Callable[[], ProgrammedAgentInstructionResult[T]]): The
                operation to execute atomically.

        Returns:
            ProgrammedAgentInstructionResult[T]: The result of the operation.

        Raises:
            RuntimeError: If an operation is already in progress.
        """
        if not self._operation_lock.acquire(blocking=False):
            raise RuntimeError("Operation already in progress")

        try:
            result = callback()
            self._last_message_role = result.agent_message.role_name
            return result
        finally:
            self._operation_lock.release()

    def repair_state(self, requirement: ProgrammableAgentRequirement) -> None:
        r"""Repair the state of the agent.

        Implements basic state repair for message role requirements.

        Args:
            requirement (ProgrammableAgentRequirement): The requirement to
                repair the state for.
        """
        if requirement == ProgrammableAgentRequirement.LAST_MESSAGE_NOT_USER:
            if self._last_message_role == "user":
                raise NotImplementedError(
                    "Must implement repair for LAST_MESSAGE_NOT_USER"
                )
