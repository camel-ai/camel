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
from typing import Any, Literal, Optional

from terminal_bench.agents.agent_name import (
    AgentName,  # type: ignore[import-not-found]
)
from terminal_bench.agents.base_agent import (  # type: ignore[import-not-found]
    AgentResult,
    BaseAgent,
)
from terminal_bench.handlers.trial_handler import (
    TrialHandler,  # type: ignore[import-not-found]
)
from terminal_bench.harness import Harness  # type: ignore[import-not-found]
from terminal_bench.terminal.tmux_session import (
    TmuxSession,  # type: ignore[import-not-found]
)

from camel.agents import ChatAgent

from .base import BaseBenchmark


class TerminalBench(Harness):
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

    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        randomize: bool = False,
        subset: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> "BaseBenchmark":
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
