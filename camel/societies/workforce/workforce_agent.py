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

from camel.messages import BaseMessage
from camel.societies.workforce import Workforce
from camel.tasks import Task


class WorkforceAgent:
    r"""Wraps a Workforce as a single-agent interface for benchmarking.  
    Internally, WorkforceAgent:
      1. Creates a Workforce named `workforce_name`.  
      2. Registers each ChatAgent from `agents_config` as a worker under that Workforce.  
      3. On `step(user_message)`, builds a Task combining:
         • `task_instruction` + "\nReturn ONLY the final answer as the solution."
         • `additional_info=user_message`
      4. Calls `Workforce.process_task(...)`, letting child workers collaborate.
      5. Extracts the final `result` and returns it in a DummyResponse, mirroring a ChatAgent API.

    Args:
        agents_config (List[Dict]):  
            Each dict has:
              - 'agent' (ChatAgent): Worker to register.
              - 'description' (str): Label for that worker.
        workforce_name (str): Name for the underlying Workforce.
        task_instruction (str): Fixed instruction template (e.g., “Evaluate this summary for accuracy.”).
            Appended to each user message at inference time.

    Methods:
        __init__(agents_config, workforce_name, task_instruction):
            - Instantiates a Workforce.
            - Registers each ChatAgent as a SingleAgentWorker.
            - Stores `task_instruction` for later tasks.

        step(user_message: str) -> DummyResponse:
            - Creates a Task(content=..., additional_info=user_message).
            - Runs `self.workforce.process_task(...)` synchronously.
            - Wraps `result_task.result` into a BaseMessage and DummyResponse.
            - Returns DummyResponse so downstream benchmarks treat it like any ChatAgent.
    """
    def __init__(self, agents_config, workforce_name, task_instruction):
        self.agents_config = agents_config
        self.workforce = Workforce(workforce_name)
        self.task_instruction = task_instruction

        for config in agents_config:
            agent = config['agent']
            description = config['description']
            self.workforce.add_single_agent_worker(description, worker=agent)

    def step(self, user_message: str) -> DummyResponse:
        task_instructions = (
                self.task_instruction + "\n"
                "Return ONLY the final answer as the solution."
        )

        task = Task(
            content=task_instructions,
            additional_info=user_message,
            id="0"
        )

        # Run the workforce committee
        result_task = self.workforce.process_task(task)
        final_answer = result_task.result

        # Wrap as a ChatAgent-style message
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
        # Store the single BaseMessage inside a list named 'msgs', matching ChatAgent output.
        self.msgs = [msg]
