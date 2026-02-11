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
When a task fails, the worker retains the agent instance (with its conversation
history intact) and reuses it directly on the next retry attempt, instead of
creating a fresh agent.

This example:
- First attempt: Mocked to FAIL (simulating partial work done)
- Second attempt: Real API call with the same agent, history preserved
"""

import asyncio
from unittest.mock import MagicMock

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.utils import TaskResult
from camel.tasks.task import Task
from camel.types import ModelPlatformType, ModelType, OpenAIBackendRole


async def main():
    print("=" * 70)
    print("Breakpoint Resume Demo")
    print("=" * 70)
    print(
        "\nThis demo shows how the agent instance is retained across retries."
    )
    print("- First attempt: Mocked to FAIL with partial work saved")
    print("- Second attempt: Same agent reused with history intact\n")

    # Create system message
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Research Assistant",
        content="You are a research assistant that helps with tasks.",
    )

    # Create agent with a real model for the second attempt
    agent = ChatAgent(
        system_message=sys_msg,
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    call_count = 0

    # Save the real astep for the second call
    real_astep = agent.astep

    async def astep_toggle(prompt, *args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call: simulate partial work then fail
            agent.update_memory(
                BaseMessage.make_user_message(
                    role_name="user",
                    content=(
                        "[Progress] Started researching quantum "
                        "computing..."
                    ),
                ),
                OpenAIBackendRole.USER,
            )
            agent.update_memory(
                BaseMessage.make_assistant_message(
                    role_name="assistant",
                    content=(
                        "[Progress] Found: Feynman proposed quantum "
                        "computing in 1981. Shor's algorithm was "
                        "discovered in 1994..."
                    ),
                ),
                OpenAIBackendRole.ASSISTANT,
            )

            print(
                "  -> Agent did partial work (added to conversation history)"
            )
            print("  -> Returning FAILED result")

            response = MagicMock()
            response.msg = MagicMock(
                parsed=TaskResult(
                    content=(
                        "Incomplete: Connection timeout while fetching "
                        "sources"
                    ),
                    failed=True,
                ),
                content=(
                    '{"content":"Incomplete: Connection timeout",'
                    '"failed":true}'
                ),
            )
            response.info = {}
            return response
        else:
            # Second call: use real API
            return await real_astep(prompt, *args, **kwargs)

    agent.astep = astep_toggle

    # Create worker
    worker = SingleAgentWorker(
        "Research assistant",
        agent,
        use_agent_pool=False,
        enable_breakpoint_resume=True,
        use_structured_output_handler=False,
    )

    # Override to provide our test agent
    first_call = True

    async def get_agent():
        nonlocal first_call
        if first_call:
            first_call = False
            return agent
        raise AssertionError("Should reuse retained agent")

    async def return_agent(a):
        pass

    worker._get_worker_agent = get_agent
    worker._return_worker_agent = return_agent

    # Create task
    task = Task(
        content=(
            "Research quantum computing history and list 3 key milestones."
        ),
        id="task-1",
    )

    # ========== FIRST ATTEMPT (MOCKED FAIL) ==========
    print("-" * 70)
    print("[FIRST ATTEMPT - Mocked Failure]")
    print("-" * 70)

    state = await worker._process_task(task, [])

    print(f"\nResult: {state}")
    print(f"Task result: {task.result}")

    # Show retained agent info
    if task.id in worker._failed_task_agents:
        retained = worker._failed_task_agents[task.id]
        records = retained.memory.retrieve()
        print(f"\nAgent retained with {len(records)} memory records:")
        for record in records:
            role = record.memory_record.role_at_backend
            content = record.memory_record.message.content[:70]
            print(f"    [{role}] {content}...")

    # ========== SECOND ATTEMPT (REAL API) ==========
    print("\n" + "-" * 70)
    print("[SECOND ATTEMPT - Real API Call]")
    print("-" * 70)

    # Note: In real usage with Workforce, failure_count is auto-incremented.
    # We set it manually here because we're calling _process_task() directly.
    task.failure_count = 1

    print("\nCalling real API with the same agent (history preserved)...")
    print("The agent will receive:")
    print("  1. Its existing conversation history (partial work)")
    print("  2. A retry message explaining the failure\n")

    state = await worker._process_task(task, [])

    print(f"\nResult: {state}")
    print(f"Task result:\n{task.result}")

    # ========== VERIFY ==========
    print("\n" + "-" * 70)
    print("[VERIFICATION]")
    print("-" * 70)

    # Check agent's memory for retained content
    memory_contents = [
        r.memory_record.message.content for r in agent.memory.retrieve()
    ]

    has_previous = any(
        "Feynman" in c or "Progress" in c for c in memory_contents
    )
    has_retry = any("Retry attempt" in c for c in memory_contents)

    print(f"  Previous context preserved: {'YES' if has_previous else 'NO'}")
    print(f"  Retry message injected:     {'YES' if has_retry else 'NO'}")
    print(
        "  Agent retained after success: "
        f"{'NO' if task.id not in worker._failed_task_agents else 'YES'}"
    )

    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
