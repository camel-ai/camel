# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Breakpoint Resume Example
=========================

This example demonstrates the breakpoint resume feature of SingleAgentWorker.
When a task fails, the worker saves its conversation history to
`task.execution_context`. On retry, the history is restored so the agent can
continue from where it left off instead of starting from scratch.

Key features demonstrated:
1. Automatic saving of conversation history on task failure
2. Automatic restoration of history on retry
3. Retry context message describing the failure reason

This example:
- First attempt: Mocked to FAIL (simulating partial work done)
- Second attempt: Real API call with restored context
"""

import asyncio
from typing import List
from unittest.mock import MagicMock

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.utils import TaskResult
from camel.tasks.task import Task
from camel.types import ModelPlatformType, ModelType, OpenAIBackendRole


class BreakpointResumeDemo(SingleAgentWorker):
    """A demo worker with controlled first failure, then real API retry."""

    def __init__(self, description: str, agents: List[ChatAgent]):
        super().__init__(
            description,
            agents[0],
            use_agent_pool=False,
            enable_breakpoint_resume=True,
            use_structured_output_handler=False,
        )
        self._demo_agents = list(agents)

    async def _get_worker_agent(self) -> ChatAgent:
        return self._demo_agents.pop(0)

    async def _return_worker_agent(self, agent: ChatAgent) -> None:
        pass


async def main():
    print("=" * 70)
    print("Breakpoint Resume Demo")
    print("=" * 70)
    print(
        "\nThis demo shows how conversation history is preserved across retries."  # noqa: E501
    )
    print("- First attempt: Mocked to FAIL with partial work saved")
    print("- Second attempt: Real API call with restored context\n")

    # Create system message
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Research Assistant",
        content="You are a research assistant that helps with tasks.",
    )

    # First agent: mocked to fail
    agent_first = ChatAgent(sys_msg)

    # Second agent: real API call
    agent_second = ChatAgent(
        system_message=sys_msg,
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    # Mock first agent to FAIL (simulating partial work)
    async def astep_fail(prompt, *args, **kwargs):
        # Simulate agent doing some work before failing
        agent_first.update_memory(
            BaseMessage.make_user_message(
                role_name="user",
                content="[Progress] Started researching quantum computing...",
            ),
            OpenAIBackendRole.USER,
        )
        agent_first.update_memory(
            BaseMessage.make_assistant_message(
                role_name="assistant",
                content="[Progress] Found: Feynman proposed quantum computing in 1981. "  # noqa: E501
                "Shor's algorithm was discovered in 1994...",
            ),
            OpenAIBackendRole.ASSISTANT,
        )

        print("  -> Agent did partial work (added to conversation history)")
        print("  -> Returning FAILED result")

        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(
                content="Incomplete: Connection timeout while fetching sources",  # noqa: E501
                failed=True,
            ),
            content='{"content":"Incomplete: Connection timeout","failed":true}',  # noqa: E501
        )
        response.info = {}
        return response

    agent_first.astep = astep_fail

    # Create worker
    worker = BreakpointResumeDemo(
        "Research assistant", [agent_first, agent_second]
    )

    # Create task
    task = Task(
        content="Research quantum computing history and list 3 key milestones.",  # noqa: E501
        id="task-1",
    )

    # ========== FIRST ATTEMPT (MOCKED FAIL) ==========
    print("-" * 70)
    print("[FIRST ATTEMPT - Mocked Failure]")
    print("-" * 70)

    state = await worker._process_task(task, [])

    print(f"\nResult: {state}")
    print(f"Task result: {task.result}")

    # Show saved execution context
    if task.execution_context:
        history = task.execution_context.get("conversation_history", [])
        print("\nSaved to execution_context:")
        print(f"  conversation_history: {len(history)} records")

        print("\n  Saved conversation preview:")
        for record in history:
            role = record.get("role_at_backend", "?")
            content = record.get("message", {}).get("content", "")[:70]
            print(f"    [{role}] {content}...")

    # ========== SECOND ATTEMPT (REAL API) ==========
    print("\n" + "-" * 70)
    print("[SECOND ATTEMPT - Real API Call]")
    print("-" * 70)

    # Note: In real usage with Workforce, failure_count is auto-incremented.
    # We set it manually here because we're calling _process_task() directly.
    task.failure_count = 1

    print("\nCalling real API with restored context...")
    print("The agent will receive:")
    print("  1. Previous conversation history (partial work)")
    print("  2. Retry message explaining the failure\n")

    state = await worker._process_task(task, [])

    print(f"\nResult: {state}")
    print(f"Task result:\n{task.result}")

    # ========== VERIFY ==========
    print("\n" + "-" * 70)
    print("[VERIFICATION]")
    print("-" * 70)

    # Check agent_second's memory for restored content
    memory_contents = [
        r.memory_record.message.content for r in agent_second.memory.retrieve()
    ]

    has_previous = any(
        "Feynman" in c or "Progress" in c for c in memory_contents
    )
    has_retry = any("Retry attempt" in c for c in memory_contents)

    print(f"  Previous context restored: {'YES' if has_previous else 'NO'}")
    print(f"  Retry message injected:    {'YES' if has_retry else 'NO'}")

    if task.execution_context:
        retry_ctx = task.execution_context.get("retry_context", "")
        if retry_ctx:
            print(f"\n  Retry context: {retry_ctx[:60]}...")

    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
