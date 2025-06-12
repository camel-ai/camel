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

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

from terminal_bench.terminal.terminal import Terminal, spin_up_terminal

from camel.environments.base import MultiStepEnv
from camel.environments.models import Action, Observation
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger

logger = get_logger(__name__)


class TerminalBenchEnv(MultiStepEnv):
    r"""A temporary skeleton

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

        # Docker logic
        self._terminal_ctx: contextmanager | None = None
        self._terminal: Terminal | None = None
        self._container = None
        self._session = None

        # Termination logic
        self.execution_result: int | None = None

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Draw a task from the Terminal Bench dataset.

        Currently, terminal bench holds 93 tasks. In this implementation we will simply draw
        a random sample from this dataset.

        Returns:
            A dictionary representing the initial state.
        """
        pass

    async def _setup_docker(self, task: str) -> None:
        r"""Setup tmux sessions and run install script for the specified task.

        This method reuses the existing setup logic in terminal bench to spinup a tmux
        session for a task.

        Args:
            task: The task we want to create a session for
        """

        if self._terminal is not None:
            logger.warning(
                "_setup_docker() called twice - Please teardown the previous session first"
            )

        # TODO implement proper task selection depending on StaticDataset structure
        compose_path = Path("tasks") / task / "docker-compose.yml"
        if not compose_path.exists():
            raise FileNotFoundError(compose_path)

        # Depend on docker-compose.yml
        client_container = f"{task}-client"
        client_image = f"{task}-image"

        self._terminal_ctx = spin_up_terminal(
            client_container_name=client_container,
            client_image_name=client_image,
            docker_compose_path=compose_path,
            docker_name_prefix="tb",
            no_rebuild=True,
            cleanup=False,
            livestream=False,
        )

        self._terminal = self._terminal_ctx.__enter__()  # start container
        self._session = self._terminal.create_session("agent")
        self._container = self._terminal.container

        logger.info(
            "Docker stack for '%s' is ready (container %s)",
            task,
            self._container.name,
        )

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

    def _is_done(self) -> bool:
        r"""Checks for environment-specific termination conditions.

        Max step condition is checked in Parentclass, so here we will
        check if the correct final solution has been reached.

        Returns:
            True if execution result is 0, false otherwise.
        """

        return True if self.execution_result == 0 else False
