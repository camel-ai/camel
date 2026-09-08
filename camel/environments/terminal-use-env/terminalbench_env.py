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

import asyncio
import os
import random
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
from camel.environments.terminal_use_env.docker_terminal.terminal import Terminal, spin_up_terminal

from camel.environments.base import MultiStepEnv
from camel.environments.models import Action, Observation
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger

logger = get_logger(__name__)

SYS_PROMPT = r"""
    You are an expert system administrator operating within a terminal 
    environment. Your goal is to solve the given task by issuing a 
    sequence of commands. You will be provided with the task description 
    and the history of commands and their outputs.

    Its imperative that you end your response with the final solution 
    (the command to be run) wrapped inside of a latex boxed statement.

    e.g.

    \\boxed{ls -a}

    The task description and the terminal output so far is:

    """


class TerminalBenchEnv(MultiStepEnv):
    r"""A temporary skeleton

    Attributes:
        extractor (BaseExtractor): An extractor to process LLM responses.
    """

    def __init__(
        self,
        extractor: BaseExtractor,
        cache_dir: str | None = None,
        task_sampling: bool = True,
        terminal_context_window: int = 4096,
        **kwargs: Any,
    ) -> None:
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

        self._task_sampling = task_sampling
        self._task = None
        self._task_config: Dict[str, Any] = {}
        self._last_command = ""
        self._reward_dict = {}
        # Termination logic
        self.execution_result: int | None = None

        # Download the dataset
        self._download_dataset(cache_dir=cache_dir)

        # context specific parameters
        self.terminal_context_window = terminal_context_window

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Draw a task from the Terminal Bench dataset.

        Currently, terminal bench holds 93 tasks. In this implementation we
        will simply draw a random sample from this dataset.

        Returns:
            A dictionary representing the initial state.
        """
        # Load task.yml as a dict from the tasks directory
        tasks_root = Path(self._cache_dir) / "tasks"
        task_directories = [
            task.name for task in tasks_root.iterdir() if task.is_dir()
        ]

        if not task_directories:
            raise RuntimeError()

        if self._task_sampling:
            self._task = random.choice(task_directories)
        else:
            if self._task is None:
                raise RuntimeError()

        # Load the task configuration
        try:
            with (tasks_root / self._task / "task.yaml").open() as f:
                self._task_config = yaml.safe_load(f)
            logger.info(
                f"Successfully loaded task configuration for {self._task}"
            )
        except yaml.YAMLError as e:
            logger.error(f"Error parsing the task configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading the task configuration file: {e}")
            raise

        # Setup the docker container for the task

        self._setup_docker(self._task)

        # Initialize the state
        state = {
            "TerminalHistory": "",
        }

        return state

    def select_task(self, task: str) -> None:
        self._task = task

    def _setup_docker(self, task: str) -> None:
        r"""Setup tmux sessions and run install script for the specified task.

        This method reuses the existing setup logic in terminal bench to
        spinup a tmux session for a task.

        Args:
            task: The task we want to create a session for
        """

        if self._terminal is not None:
            logger.warning(
                "_setup_docker() called twice - Please teardown the previous "
                "session first"
            )

        compose_path = (
            Path(self._cache_dir) / "tasks" / task / "docker-compose.yml"
        )
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
            no_rebuild=False,
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
        if self._session is None:
            raise RuntimeError(
                "Tmux session not initialised; call reset() first."
            )

        command = await self._extract_command(action)
        self._last_command = command

        logger.debug("Executing command: %s", command)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._session.send_keys([command, "Enter"], block=True),
        )

        terminal_output = self._session.capture_pane(capture_entire=True)

        self._state["TerminalHistory"] = terminal_output

    async def _extract_command(self, action: Action) -> str:
        r"""Helper function to facilitate using different extraction
        strategies.

        Default implementation will expect a BoxedExtractor with the
        BoxedStrategy.

        Important: Do not forget to adapt the SYS_PROMPT to the extraction
        strategy used.

        Args:
            action: The action taken by the agent.

        Returns:
            str: The extracted command to be run in the tmux session
        """

        command: str = await self.extractor.extract(action.llm_response)

        return command.strip()

    def _get_next_observation(self) -> Observation:
        r"""Generates the observation for the next step.

        This method returns the next question for the environment. It uses a
        sliding window approach to manage the terminal history, keeping the
        first 'head' and last 'tail' interactions to prevent the context from
        growing too large while preserving critical information.

        The questions is composed of the state, task instruction and system
        prompt.
        self._state: TerminalHistory : str

        Returns:
            An Observation object for the agent.
        """
        try:
            task_instruction = (
                f"## Task Goal:\n{self._task_config['instruction']}"
            )
        except KeyError as e:
            logger.error(f"Task configuration missing key: {e}")
            raise ValueError(
                f"Task configuration is missing the required key: {e}"
            )

        history_log = []
        terminal_history = self._state.get("TerminalHistory", "")

        history_len = len(terminal_history)

        if history_len == 0:
            history_log.append(
                "The terminal is ready. No commands have been executed yet."
            )
        else:
            # If the history is too long, apply something
            # TODO make logs better
            history_log.append(
                f"We are at step {self._current_step} and the history is "
                "not yet full"
            )
            if history_len > self.terminal_context_window:
                history_log.append(
                    "History exceeded context window, truncating"
                )
                terminal_history = terminal_history[
                    -self.terminal_context_window :
                ]

        prompt_parts = [
            SYS_PROMPT,
            task_instruction,
            terminal_history,
            "Based on the task and the terminal history, what is the next "
            "command we should execute?",
        ]
        obs = "\n\n".join(prompt_parts)

        observation = Observation(question=obs, context={}, metadata={})
        return observation

    def _get_terminal_observation(self) -> Observation:
        r"""Generates the final observation when an episode ends.

        TODO: Decide upon terminal obs

        Returns:
            A final Observation for the agent.
        """
        obs = (
            f"The terminal session has ended after {self._current_step} "
            "steps. The task is over"
        )
        return Observation(question=obs, context={}, metadata={})

    async def compute_reward(self) -> Tuple[float, Dict[str, float]]:
        r"""Calculates the reward for the current state.

        This method will temporarily return 1 for the final correct step,
        and 0 for all others until a proper verifier/Intermediate reward
        assigner has been thought of.

        Returns:
            A tuple containing the total reward (float) and a dictionary
            with all past rewards.
        """

        self.execution_result = self._container.exec_run(
            ["bash", "/tests/run-tests.sh"],
            workdir="/tests",
        )

        if self.execution_result.exit_code == 0:
            reward = 1.0
        else:
            reward = 0.0

        self._reward_dict[self._last_command] = reward

        return reward, self._reward_dict

    def _is_done(self) -> bool:
        r"""Checks for environment-specific termination conditions.

        Max step condition is checked in Parentclass, so here we will
        check if the correct final solution has been reached.

        Returns:
            True if execution result is 0, false otherwise.
        """

        return bool(self.execution_result.exit_code == 0)

    def _download_dataset(self, cache_dir: str) -> None:
        r"""Download dataset from terminal bench github repository to cache_dir.

        Args:
            cache_dir: Directory where the dataset will be cached.

        Returns:
            None: This method should not return anything.
        """
        if cache_dir is None:
            # default to <current script path>/.cache
            cache_dir = f"{Path(__file__).parent}/.cache/"

        self._cache_dir = cache_dir
        cache_path = Path(cache_dir)
        tasks_dir = cache_path / "tasks"

        if tasks_dir.is_dir():
            logger.info("Tasks directory already present at %s", tasks_dir)
            return

        cache_path.mkdir(parents=True, exist_ok=True)

        svn_cmd = [
            "svn",
            "export",
            "https://github.com/laude-institute/terminal-bench/tree/main/tasks",
            str(tasks_dir),
        ]

        logger.info("Attempting SVN export of Terminal-Bench tasks …")
        svn_ok = subprocess.run(svn_cmd, check=False).returncode == 0

        if svn_ok and tasks_dir.is_dir():
            logger.info(
                "SVN export succeeded → dataset cached at %s", tasks_dir
            )
            return

        logger.warning(
            "SVN export failed or `svn` not installed; falling "
            "back to temporary git clone."
        )

        # Create a temporary directory for cloning
        temp_dir = os.path.join(cache_dir, "temp_repo")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        try:
            # Clone the entire repository temporarily
            logger.info("Cloning terminal-bench repository...")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "https://github.com/laude-institute/terminal-bench.git",
                    temp_dir,
                ],
                check=True,
            )

            # Copy only the tasks folder
            source_tasks = os.path.join(temp_dir, "tasks")
            if os.path.exists(source_tasks):
                shutil.copytree(source_tasks, tasks_dir)
                logger.info(f"Successfully downloaded tasks to {tasks_dir}")
            else:
                raise FileNotFoundError(
                    "Tasks directory not found in the repository at "
                    f"{source_tasks}"
                )

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise
        except Exception as e:
            logger.error(f"Error downloading dataset: {e}")
            raise
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _close(self) -> None:
        if self._terminal_ctx is not None:
            self._terminal_ctx.__exit__(None, None, None)
