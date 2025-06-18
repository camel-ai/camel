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

import uuid
from typing import Dict, List, Optional

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.societies.workforce import Workforce
from camel.tasks import Task

logger = get_logger(__name__)


class WorkforceAgent:
    r"""Wraps a Workforce as a single‑agent interface for benchmarking.

    Internal workflow:
    1. Create a Workforce named `workforce_name`.
    2. Register each ChatAgent from `agents_config` as a worker.
    3. When `step(user_message)` is called, build a Task whose content is
       `task_instruction` + " Return ONLY the final answer as the solution." and whose
       `additional_info` holds the original user_message.
    4. Delegate to `Workforce.process_task(...)` so the workers collaborate.
    5. Return the result in a DummyResponse that mimics the ChatAgent API.

    Arguments:
        agents_config (List[Dict]):
            Each dict must contain:
              - 'agent' : a ChatAgent instance to be registered.
              - 'description' : a human‑readable label for that worker.
        workforce_name (str):
            Name assigned to the underlying Workforce.
        task_instruction (str):
            Instruction template that is prepended to every task.
        workforce_kwargs (dict, optional):
            Extra options forwarded to Workforce(...):
              coordinator_agent_kwargs         : overrides for the coordinator agent.
              task_agent_kwargs                : default kwargs for SingleAgentWorker instances.
              new_worker_agent_kwargs          : kwargs used when creating new workers dynamically.
              graceful_shutdown_timeout (int)  : seconds to wait before force‑closing.

    Methods:
        __init__(agents_config, workforce_name, task_instruction, workforce_kwargs=None):
            Build the Workforce and register workers.
        step(user_message: str) -> DummyResponse:
            Run the task and return a DummyResponse containing the final answer.
    """

    def __init__(
        self,
        agents_config: List[Dict],
        workforce_name: str,
        task_instruction: str,
        workforce_kwargs: Optional[Dict] | None = None,
    ):
        self.task_instruction = task_instruction

        self.workforce = Workforce(workforce_name, **(workforce_kwargs or {}))

        for cfg in agents_config:
            agent = cfg["agent"]
            description = cfg.get("description", agent.role_name)
            self.workforce.add_single_agent_worker(description, worker=agent)


    def step(self, user_message: str) -> "DummyResponse":
        """Delegate the query to the Workforce and return a ChatAgent-style response."""

        task = Task(
            # put BOTH the instruction and the user’s question in the content
            content=f"{self.task_instruction}\n\n{user_message}",
            id=str(uuid.uuid4()),
            # additional_info is optional and defaults to {}, so just omit it
            # or use: additional_info={"user_message": user_message}
        )

        try:
            result_task = self.workforce.process_task(task)
            final_answer = result_task.result or "[Task finished without result]"
        except Exception as exc:
            logger.error("WorkforceAgent – processing error: %s", exc)
            final_answer = f"[Workforce error] {exc}"

        self.workforce.reset()

        reply_msg = BaseMessage.make_assistant_message(
            role_name="assistant", content=final_answer
        )
        return DummyResponse(reply_msg)


class DummyResponse:
    r"""A minimal wrapper that adapts a single BaseMessage into the ChatAgent-style response format.

    Benchmarks and downstream code often expect the agent’s output to be accessible via:
        response.msgs[0].content

    Instead of returning a raw BaseMessage (or a list of messages), DummyResponse ensures:
    1. `self.msgs` is always a list of BaseMessage instances.
    2. Code can do `response.msgs[0].content` without modification.

    Args:
        msg (BaseMessage):
            The assistant’s reply (normally created with
            BaseMessage.make_assistant_message(role_name="assistant", content=...)).
            This single message is stored in a one-element list.

    Attributes:
        msgs (List[BaseMessage]):
            A list containing exactly the `msg` passed in. By exposing `.msgs` as a list,
            we preserve compatibility with any harness that expects to iterate over or index
            into the agent’s messages.

    Usage:
        # After computing `reply_msg` (a BaseMessage), simply wrap it:
        response = DummyResponse(reply_msg)
        # Benchmark code can then retrieve:
        answer_text = response.msgs[0].content
    """

    def __init__(self, msg: BaseMessage):
        self.msgs = [msg]
