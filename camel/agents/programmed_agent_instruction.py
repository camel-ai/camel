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
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage

T = TypeVar('T')


class ProgrammableAgentRequirement(Enum):
    LAST_MESSAGE_NOT_USER = "LAST_MESSAGE_NOT_USER"


class ProgrammedAgentInstructionResult(BaseModel, Generic[T]):
    r"""
    Result of a programmable agent instruction execution.

    Contains the messages exchanged during execution and the computed value.
    The value type is specified by the generic type parameter T.
    """

    user_message: BaseMessage
    agent_message: BaseMessage
    value: T


class AbstractProgrammableAgent(abc.ABC):
    r"""
    Abstract class for a programmable agent.

    A programmable agent is an agent that can be programmed to perform a
    specific function or task. This class defines the interface for a
    programmable
    agent.

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
        r"""
        Run an atomic operation on the agent.

        An atomic operation is an operation that is guaranteed to
        be executed without interruption by any other operation.

        If the operation fails or times out the agents state should be
        unchanged.

        If an operation is already in progress, this method should throw an
        exception. (It is up to the caller to do any queuing)

        If the agent is in a state where it can perform the operation,
        it must leave the agent in a state where it can perform the
        operation again. Though if state changes in successful operation
        improve its ability to perform the operation, it should keep them.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def repair_state(self, requirement: ProgrammableAgentRequirement) -> None:
        r"""
        Repair the state of the agent.

        Agents may have other non-atomic interfaces, such as a user interface,
        or chat between other agents.

        This method should restore the agent to a state where it can perform
        operations according to the specified requirement.
        """
        raise NotImplementedError


def programmable_capability(
    func: Callable[..., ProgrammedAgentInstructionResult[T]],
) -> Callable[..., ProgrammedAgentInstructionResult[T]]:
    r"""
    Decorator for programmable agent capabilities.

    Wraps a method to ensure it is executed atomically via the agent's
    run_atomic interface.
    The decorated method must return a ProgrammedAgentInstructionResult with
    appropriate type parameter.
    """

    @wraps(func)
    def wrapper(
        self, *args: Any, **kwargs: Any
    ) -> ProgrammedAgentInstructionResult[T]:
        return self.run_atomic(lambda: func(self, *args, **kwargs))

    return wrapper


class ProgrammableChatAgent(ChatAgent, AbstractProgrammableAgent):
    r"""
    A chat agent that can be programmed to perform specific tasks.

    Provides a default implementation of atomic execution using threading locks
    and basic state tracking for message roles. Implementing classes need to
    provide specific repair logic for their use cases.
    """

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._operation_lock = threading.Lock()

    def run_atomic(
        self, callback: Callable[[], ProgrammedAgentInstructionResult[T]]
    ) -> ProgrammedAgentInstructionResult[T]:
        if not self._operation_lock.acquire(blocking=False):
            raise RuntimeError("Operation already in progress")

        try:
            result = callback()
            self._last_message_role = result.agent_message.role
            return result
        finally:
            self._operation_lock.release()

    def repair_state(self, requirement: ProgrammableAgentRequirement) -> None:
        if requirement == ProgrammableAgentRequirement.LAST_MESSAGE_NOT_USER:
            if self._last_message_role == "user":
                raise NotImplementedError(
                    "Must implement repair for LAST_MESSAGE_NOT_USER"
                )


from camel.agents.multi_hop_generator_agent import MultiHopGeneratorAgent
