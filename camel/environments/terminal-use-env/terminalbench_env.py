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
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
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

    def __init__(
        self,
        extractor: BaseExtractor,
        task: str,
        cache_dir: str | None = None,
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

        self._task = task
        self._task_config: Dict[str, Any] = {}

        """Task configuration example:
                instruction: |-
                For some reason I can't curl example.com, can you figure out why and what I should do to fix it?
                author_name: Nicholas Carlini
                author_email: nicholas@carlini.com
                difficulty: medium
                category: system-administration
                tags:
                - sys-admin
                - networking
                - troubleshooting
                parser_name: pytest
                max_agent_timeout_sec: 360.0
                max_test_timeout_sec: 120.0
                run_tests_in_same_shell: false
        """

        # Termination logic
        self.execution_result: int | None = None

        # Download the dataset
        self._cache_dir = cache_dir
        self._download_dataset(cache_dir=cache_dir)

        # setup some parameters for interaction history
        self.max_history_head = kwargs.get(
            'max_history_head', 5
        )  # Number of initial interactions to always keep
        self.max_history_tail = kwargs.get(
            'max_history_tail', 10
        )  # Number of last interactions to always keep

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Draw a task from the Terminal Bench dataset.

        Currently, terminal bench holds 93 tasks. In this implementation we will simply draw
        a random sample from this dataset.

        get_initial_state() is called at the start of each episode, within reset().
        it load a task configuration from the dataset _cache_dir/tasks/<task_name>/task.yaml

        it will then setup the docker container for the task and return

        it returns a state dictionary
        containing the initial state of the environment, including terminal history.
        TerminalHistory : List[Tuple[Command, Output]] = []

        Returns:
            A dictionary representing the initial state.
        """
        # Load task.yml as a dict from the tasks directory
        task_path = f"{self._cache_dir}/tasks/{self._task}/task.yaml"
        if not os.path.exists(task_path):
            logger.error(f"Task configuration file not found: {task_path}")
            raise FileNotFoundError(
                f"Task configuration file not found: {task_path}"
            )

        # Load the task configuration
        try:
            with open(task_path, 'r') as f:
                self._task_config = yaml.safe_load(f)
            logger.info(
                f"Successfully loaded task configuration from {task_path}"
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
            "TerminalHistory": [],
        }

        return state

    def _setup_docker(self, task: str) -> None:
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

        logger.debug("Executing command: %s", command)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._session.send_keys([command, "Enter"], block=True),
        )

        terminal_output = self._session.capture_pane(capture_entire=True)

        self._state["TerminalHistory"] = terminal_output

    async def _extract_command(self, action: Action) -> str:
        r"""Helper function to facilitate using different extraction strategies.

        Default implementation will expect a BoxedExtractor with the BoxedStrategy.

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

        The questions is composed of the state, task instruction and system prompt.
        self._state: TerminalHistory : List[Tuple[Command, Output]]

        example task instruction:
            For some reason I can't curl example.com, can you figure out why and what I should do to fix it?

        Returns:
            An Observation object for the agent.
        """
        # 1. Define a system prompt to instruct the AI on its role and task.
        system_prompt = (
            "You are an expert system administrator operating within a terminal environment. "
            "Your goal is to solve the given task by issuing a sequence of commands. "
            "You will be provided with the task description and the history of "
            "commands and their outputs. Your response must be only the raw command to be "
            "executed, without any explanation, formatting, or additional text."
        )

        # 2. Retrieve the specific task instruction for the current episode.
        try:
            task_instruction = (
                f"## Task Goal:\n{self._task_config['instruction']}"
            )
        except KeyError as e:
            logger.error(f"Task configuration missing key: {e}")
            raise ValueError(
                f"Task configuration is missing the required key: {e}"
            )
        # 3. Format the terminal history using the sliding window strategy.
        history_log = []
        terminal_history = self._state.get("TerminalHistory", [])

        history_len = len(terminal_history)

        if history_len == 0:
            history_log.append(
                "The terminal is ready. No commands have been executed yet."
            )
        else:
            # If the history is too long, apply the head/tail windowing
            if history_len > self.max_history_head + self.max_history_tail:
                # Add the first 'head' interactions
                head = terminal_history[: self.max_history_head]
                for command, output in head:
                    history_log.append(
                        f"$ Command: {command}\nOutput:{output}"
                    )

                # Add a placeholder for the omitted middle part
                omitted_count = history_len - (
                    self.max_history_head + self.max_history_tail
                )
                history_log.append(
                    f"\n[... {omitted_count} previous interactions omitted for brevity ...]\n"
                )

                # Add the last 'tail' interactions
                tail = terminal_history[-self.max_history_tail :]
                for command, output in tail:
                    history_log.append(
                        f"$ Command: {command}\nOutput:{output}"
                    )
            else:
                # If history is short enough, show all of it
                for command, output in terminal_history:
                    history_log.append(
                        f"$ Command: {command}\nOutput:{output}"
                    )

        formatted_history = "\n".join(history_log)
        history_section = f"## Terminal History:\n{formatted_history}"

        # 4. Assemble the complete prompt (question) for the language model.
        prompt_parts = [
            system_prompt,
            task_instruction,
            history_section,
            "Based on the task and the terminal history, what is the next command you will execute?",
        ]
        obs = "\n\n".join(prompt_parts)

        # 5. Create and return the Observation object.
        observation = Observation(question=obs, context={}, metadata={})
        return observation

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

        self.execution_result = self._container.exec_run(
            ["bash", "/tests/run-tests.sh"],
            workdir="/tests",
        )

        if self.execution_result.exit_code == 0:
            reward = 1.0
        else:
            reward = 0.0

        return reward, {"": reward}

    def _is_done(self) -> bool:
        r"""Checks for environment-specific termination conditions.

        Max step condition is checked in Parentclass, so here we will
        check if the correct final solution has been reached.

        Returns:
            True if execution result is 0, false otherwise.
        """

        return bool(self.execution_result.exit_code == 0)

    def _download_dataset(self, cache_dir: str) -> None:
        r"""Downloads the Terminal Bench dataset.
        whole folder from https://github.com/laude-institute/terminal-bench/tree/main/tasks
        This method should download the dataset from the official source
        and prepare it for use in the environment.

        Example folder structure for one task:
        tasks/
        ├── build-linux-kernel-qemu/
            ├── Dockerfile
            ├── docker-compose.yaml
            ├── init.sh
            ├── run-tests.sh
            ├── solution.sh
            ├── task.yaml
            └── tests/
                ├── run-uv-pytest.sh
                ├── setup-uv-pytest.sh
                └── test_outputs.py
        """
        if cache_dir is None:
            # default to <current script path>/.cache
            cache_dir = f"{Path(__file__).parent}/.cache/"
        self._cache_dir = cache_dir

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Path to the tasks directory
        tasks_dir = os.path.join(cache_dir, "tasks")

        # Check if tasks directory already exists
        if os.path.exists(tasks_dir) and os.path.isdir(tasks_dir):
            logger.info(f"Tasks directory already exists at {tasks_dir}")
            return

        # Create a temporary directory for cloning
        temp_dir = os.path.join(cache_dir, "temp_repo")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        try:
            # Clone the repository
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

            # Copy only the tasks folder to cache_dir
            source_tasks = os.path.join(temp_dir, "tasks")
            if os.path.exists(source_tasks):
                shutil.copytree(source_tasks, tasks_dir)
                logger.info(f"Successfully downloaded tasks to {tasks_dir}")
            else:
                raise FileNotFoundError(
                    f"Tasks directory not found in the repository at {source_tasks}"
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
