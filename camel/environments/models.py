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

from typing import Any, Protocol, Tuple

from pydantic import BaseModel, Field

from camel.messages import BaseMessage


class Action(BaseModel):
    r"""Represents an action taken by an agent in an environment.

    Attributes:
        message (BaseMessage): The action message.
        metadata (Dict[str, Any]): Additional metadata such as model
            parameters, prompt details, or response confidence scores.
    """

    message: BaseMessage = Field(..., description="The action message")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the generation",
    )


class Observation(BaseModel):
    r"""Represents an observation of the environment.

    Attributes:
        message: BaseMessage The observation message.
        metadata: Optional metadata about the observation.
    """

    message: BaseMessage = Field(..., description="The observation message")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the observation",
    )


class StepResult(BaseModel):
    r"""Result of an environment step.

    Attributes:
        observation: The next observation.
        reward: Dictionary of reward scores for different aspects.
        done: Whether the episode is complete.
        info: Additional information about the step.
    """

    observation: Observation = Field(..., description="The next observation")
    reward: float = Field(..., description="Total reward of the action")
    done: bool = Field(..., description="Whether the episode is complete")
    info: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional information about the step",
    )

    def as_tuple(
        self,
    ) -> Tuple[Observation, float, bool, dict[str, Any]]:
        r"""Returns all fields of the model as a tuple, in declaration order"""
        return (self.observation, self.reward, self.done, self.info)


class Environment(Protocol):
    async def reset(self) -> Observation:
        r"""Reset the environment to an initial state.

        Returns:
            Initial observation for the episode
        """
        ...

    async def step(self, action: Action) -> StepResult:
        r"""Take a step in the environment.

        Args:
            action: Action containing everything that is needed
            to progress in the environment

        Returns:
            StepResult containing next observation, reward, done flag, and info
        """
        ...

    async def close(self) -> None:
        r"""Perform a full cleanup of all environment resources."""
        ...
