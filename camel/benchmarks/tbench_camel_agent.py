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

import logging
import os
from pathlib import Path
from typing import List, Tuple

from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.harness.models import FailureMode
from terminal_bench.terminal.tmux_session import TmuxSession

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

from .eigent_simple import developer_agent_factory

logger = logging.getLogger(__name__)


class TerminalBenchAgent(BaseAgent):
    def __init__(self, **kwargs):
        self.logging_dir = os.getenv("CAMEL_LOG_DIR", None)
        super().__init__(**kwargs)

    @staticmethod
    def name() -> str:
        return "TerminalBenchAgent"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        """Execute a task using the Terminal Bench harness.

        Args:
            instruction: The task instruction to execute
            session: TmuxSession object for command execution
            logging_dir: Optional directory for logging

        Returns:
            AgentResult with token counts and failure mode
        """

        container_name = session.container.name
        if not container_name:
            raise ValueError("Container name is required for DockerExecutor")

        run_id = 0
        while True:
            if os.path.exists(
                f"{self.logging_dir}/{container_name}_run{run_id:02d}"
            ):
                run_id += 1
            else:
                break
        session_logs_dir = (
            f"{self.logging_dir}/{container_name}_run{run_id}/session_logs/"
        )
        os.makedirs(session_logs_dir, exist_ok=True)
        working_dir = (
            f"{self.logging_dir}/{container_name}_run{run_id}/CAMEL_WORKDIR/"
        )
        os.makedirs(working_dir, exist_ok=True)

        terminal_toolkit_kwargs = {
            'timeout': 20.0,
            'working_directory': None,
            'use_docker_backend': True,
            'docker_container_name': container_name,
            'session_logs_dir': session_logs_dir,
            'safe_mode': False,
        }
        model_backend_reason = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1,
            model_config_dict={
                "stream": False,
            },
        )

        task_id = 'workforce_task'
        camel_agent = developer_agent_factory(
            model_backend_reason,
            task_id,
            terminal_toolkit_kwargs,
            system="Linux (in Docker)",
            machine="x86_64",
            is_workforce=False,
            working_directory=working_dir,
        )
        camel_agent.reset()

        usr_msg = f"{instruction}\n"

        # Get response information
        # Define a user message for creating logs directory
        usr_msg = f"Task instruction: {instruction}"
        print(f"User message: {usr_msg}")
        # Get response information
        response = camel_agent.step(usr_msg)
        print(str(response.info['tool_calls'])[:1000])

        total_input_tokens = response.info['usage']['prompt_tokens']
        total_output_tokens = response.info['usage']['completion_tokens']

        memory_list = (
            camel_agent._memory._chat_history_block.storage.memory_list
        )

        def create_timestamped_marker_from_memory(
            records: List[dict],
        ) -> Tuple[float, str]:
            """Create a timestamped marker from memory records."""
            results = []
            print(f"Total records: {len(records)}")
            for record in records:
                if 'func_name' in record['message'].keys():
                    timestamp = record['timestamp']
                    func_name = record['message']['func_name']
                    args = record['message'].get('args', {})
                    if args:
                        command = args.get('command', '')
                    else:
                        command = ''
                    results.append(
                        (
                            timestamp,
                            f"Called tool: {func_name} with args: {command}",
                        )
                    )
            return results

        timestamped_markers = create_timestamped_marker_from_memory(
            memory_list
        )

        print(f"Total input tokens: {total_input_tokens}")
        print(f"Total output tokens: {total_output_tokens}")
        print(f"Timestamped markers: {timestamped_markers}")

        del camel_agent

        return AgentResult(
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            failure_mode=FailureMode.NONE,
            timestamped_markers=timestamped_markers,
        )
