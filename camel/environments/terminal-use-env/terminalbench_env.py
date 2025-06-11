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

from typing import Any, Dict, Tuple

from camel.environments.base import MultiStepEnv
from camel.environments.models import Action, Observation
from camel.extractors.base import BaseExtractor


class TerminalBenchEnv(MultiStepEnv):
    r""" A temporary skeleton

    Attributes:
        extractor (BaseExtractor): An extractor to process LLM responses.
    """

    def __init__(self, extractor: BaseExtractor, **kwargs: Any) -> None:
        """Initializes the terminal bench environment.

        Args:
            extractor: The extractor for processing LLM outputs.
            **kwargs: Additional arguments for the parent class.
        """
        super().__init__(extractor=extractor, **kwargs)



    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Draw a task from the Terminal Bench dataset.

        Currently, terminal bench holds 93 tasks. In this implementation we will simply draw
        a random sample from this dataset.

        Returns:
            A dictionary representing the initial state.
        """
        pass

    async def _update_state(self, action: Action) -> None:
        r"""Updates the environment's state based on an action.

        This method will apply the LLM's terminal input to the environment
        and update the internal state.

        Args:
            action: The action taken by the agent.
        """
        pass

    def _get_next_observation(self) -> Observation:
        r"""Generates the observation for the next step.

        This method returns the next question for the environment
        and additional metadata

        Returns:
            An Observation object for the agent.
        """
        pass

    def _get_terminal_observation(self) -> Observation:
        r"""Generates the final observation when an episode ends.

        TODO: Decide upon terminal obs

        Returns:
            A final Observation for the agent.
        """
        pass

    async def compute_reward(self) -> Tuple[float, Dict[str, float]]:
        r"""Calculates the reward for the current state.

        This method will temporarily return 1 for the final correct step,
        and 0 for all others until a proper verifier/Intermediate reward
        assigner has been thought of.

        Returns:
            A tuple containing the total reward (float) and a dictionary
            with all past rewards.
        """
        pass

    def _is_done(self) -> bool:
        r"""Checks for environment-specific termination conditions.


        Returns:
            True if the episode has reached a terminal state, False otherwise.
        """
        pass

