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

from abc import ABC, abstractmethod

from .models import Action, Observation, StepResult


class BaseEnvironment(ABC):
    r"""Base class for all RL training environments.

    An environment ties everything together. It:
    1. Holds state and manages curriculum progression
    2. Defines reward functions and hint generation
    3. Manages dataset and task selection
    4. Provides reset and step functions
    5. Handles verifier setup and teardown
    6. Enables proactive agent behavior
    7. Supports practice environment creation
    8. Facilitates chain-of-thought verification
    """

    @abstractmethod
    async def reset(self) -> Observation:
        r"""Reset the environment to initial state.

        Returns:
            Initial observation for the episode
        """
        pass

    @abstractmethod
    async def step(self, action: Action) -> StepResult:
        r"""Take a step in the environment.

        Args:
            action: Action containing everything that is needed
            to progress in the environment

        Returns:
            StepResult containing next observation, reward, done flag, and info
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        r"""Perform a full cleanup of all environment resources."""
        pass
