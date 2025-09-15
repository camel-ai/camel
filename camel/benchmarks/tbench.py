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
import asyncio
import logging
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

if TYPE_CHECKING:
    from terminal_bench.agents.agent_name import (  # type: ignore[import-untyped]
        AgentName,
    )
    from terminal_bench.agents.base_agent import (  # type: ignore[import-untyped]
        AgentResult,
        BaseAgent,
    )
    from terminal_bench.handlers.trial_handler import (  # type: ignore[import-untyped]
        TrialHandler,
    )
    from terminal_bench.harness import Harness  # type: ignore[import-untyped]
    from terminal_bench.terminal.tmux_session import (  # type: ignore[import-untyped]
        TmuxSession,
    )
from typing_extensions import override

from camel.agents import ChatAgent

from .base import BaseBenchmark


class TerminalBench(Harness):  # type: ignore[misc]
    def __init__(
        self,
        output_path: Path,
        run_id: str,
        ChatAgent: ChatAgent,
        agent_name: AgentName | None = None,
        agent_import_path: str | None = None,
        dataset_name: str | None = None,
        dataset_version: str | None = None,
        dataset_path: Path | None = None,
        dataset_config: Path | None = None,
        registry_url: str | None = None,
        local_registry_path: Path | None = None,
        model_name: str | None = None,
        agent_kwargs: dict[str, Any] | None = None,
        no_rebuild: bool = False,
        cleanup: bool = False,
        log_level: int = logging.INFO,
        task_ids: list[str] | None = None,
        n_tasks: int | None = None,
        livestream: bool = False,
        upload_results: bool = False,
        n_concurrent_trials: int = 4,
        exclude_task_ids: list[str] | None = None,
        n_attempts: int = 1,
        global_timeout_multiplier: float = 1.0,
        global_agent_timeout_sec: float | None = None,
        global_test_timeout_sec: float | None = None,
        **kwargs,
    ):
        self.ChatAgent = ChatAgent
        super().__init__(
            output_path,
            run_id,
            agent_name,
            agent_import_path,
            dataset_name,
            dataset_version,
            dataset_path,
            dataset_config,
            registry_url,
            local_registry_path,
            model_name,
            agent_kwargs,
            no_rebuild,
            cleanup,
            log_level,
            task_ids,
            n_tasks,
            livestream,
            upload_results,
            n_concurrent_trials,
            exclude_task_ids,
            n_attempts,
            global_timeout_multiplier,
            global_agent_timeout_sec,
            global_test_timeout_sec,
            **kwargs,
        )

    r"""
        Runs the Terminal-Bench harness.

        Args:
            output_path: The path to the output directory.
                Results and logs will be written here.
            run_id: The ID of the run.
            agent_name: The name of the agent to use to generate commands.
            agent_import_path: The import path of the agent.
            dataset_name: The name of the dataset to use.
            dataset_version: The version of the dataset to use.
            dataset_path: The path to the dataset.
            dataset_config: Path to a YAML configuration file for the dataset.
                If provided, this will override dataset_name,
                dataset_version, dataset_path, task_ids, n_tasks,
                and exclude_task_ids.
            registry_url: The URL of the registry to use for the dataset.
            local_registry_path: The path to the local registry file
                to use for the dataset. If provided, will use the local
                registry instead of the remote registry.
            model_name: The name of the model to use for the agent.
            agent_kwargs: Additional keyword arguments to pass to the agent.
            no_rebuild: Whether to avoid rebuilding the Docker image.
            cleanup: Whether to remove the Docker image after the run.
            log_level: The logging level to use
                (debug, info, warning, error, critical).
            task_ids: The IDs of the tasks to run.
                If None, all tasks will be run.
            n_tasks: The number of tasks to run.
                If None, all tasks will be run.
            livestream: Whether to livestream the log file.
                Turns off all other logging
                to the console.
            upload_results: Whether to upload results to S3.
                The bucket name is read from config.
            n_concurrent_trials: Maximum number of tasks to run concurrently.
            exclude_task_ids: Set of task IDs or regex patterns to
                exclude from the run.
                Supports both exact matches and regex patterns.
            n_attempts: Number of attempts to make for each task.
            global_timeout_multiplier: Multiplier for the global
                timeout for agent runs.
            global_agent_timeout_sec: Global timeout for agent runs in seconds.
            global_test_timeout_sec: Global timeout for test runs in seconds.
        """

    async def _run_agent_with_timeout(
        self,
        trial_handler: TrialHandler,
        session: TmuxSession,
        logging_dir: Path,
        timeout_sec: float,
        agent: BaseAgent,
    ) -> AgentResult | None:
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(
            None,
            partial(
                agent.perform_task,
                instruction=trial_handler.instruction,
                session=session,
                logging_dir=logging_dir,
                camel_agent=self.ChatAgent,
            ),
        )
        return await asyncio.wait_for(task, timeout=timeout_sec)


class TBench(BaseBenchmark):
    def __init__(self, name, data_dir, save_to, processes=1):
        super().__init__(name, data_dir, save_to, processes)

    def download(self) -> "BaseBenchmark":
        return self

    def load(self, force_download: bool = False) -> "BaseBenchmark":
        return self

    @override
    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        randomize: bool = False,
        subset: Optional[int] = None,
        *args,
        **kwargs,
    ) -> "BaseBenchmark":
        r"""Run the Terminal-Bench benchmark.

        Args:
            agent: The ChatAgent to use for the benchmark.
            on: The data split to run the benchmark on.
            randomize: Whether to randomize the data.
            subset: Optional subset of tasks to run.
                If None, all tasks will be run.

        Returns:
            BaseBenchmark: The benchmark instance.
        """

        harness = TerminalBench(
            ChatAgent=agent,
            output_path=Path(self.save_to),
            run_id=datetime.now().strftime("%Y-%m-%d__%H-%M-%S"),
            dataset_name="terminal-bench-core".strip(),
            dataset_version="0.1.1",
            task_ids=None,
            n_tasks=subset,
            agent_import_path="camel.benchmarks.tbench_camel_agent:TerminalBenchAgent",
            n_concurrent_trials=self.processes,
        )
        results = harness.run()
        print(results)
        return self
