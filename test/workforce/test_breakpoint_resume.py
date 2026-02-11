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
from unittest.mock import MagicMock

import pytest

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.utils import TaskResult
from camel.tasks.task import Task, TaskState
from camel.types import OpenAIBackendRole


@pytest.mark.asyncio
async def test_breakpoint_resume_reuses_agent_instance():
    """Verify the worker retains and reuses the same agent on retry."""
    sys_msg = BaseMessage.make_assistant_message(
        role_name="tester",
        content="You are a test agent.",
    )

    agent = ChatAgent(sys_msg)
    call_count = 0

    async def astep_toggle(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        # Add some context during the first call
        if call_count == 1:
            agent.update_memory(
                BaseMessage.make_user_message(
                    role_name="user", content="first attempt context"
                ),
                OpenAIBackendRole.USER,
            )
        response = MagicMock()
        if call_count == 1:
            response.msg = MagicMock(
                parsed=TaskResult(content="failed", failed=True),
                content='{"content":"failed","failed":true}',
            )
        else:
            response.msg = MagicMock(
                parsed=TaskResult(content="ok", failed=False),
                content='{"content":"ok","failed":false}',
            )
        response.info = {}
        return response

    agent.astep = astep_toggle

    worker = SingleAgentWorker(
        "stub",
        agent,
        use_agent_pool=False,
        enable_breakpoint_resume=True,
        use_structured_output_handler=False,
    )

    # Override to provide our test agent initially
    first_call = True

    async def get_agent():
        nonlocal first_call
        if first_call:
            first_call = False
            return agent
        # Should not be called on retry when breakpoint resume is enabled
        raise AssertionError(
            "Should reuse retained agent, not request a new one"
        )

    async def return_agent(a):
        pass

    worker._get_worker_agent = get_agent
    worker._return_worker_agent = return_agent

    task = Task(content="do something", id="task1")

    # First attempt fails
    state_first = await worker._process_task(task, [])
    assert state_first == TaskState.FAILED

    # Agent should be retained in _failed_task_agents
    assert "task1" in worker._failed_task_agents

    # Second attempt succeeds (reuses the same agent)
    task.failure_count = 1
    state_second = await worker._process_task(task, [])
    assert state_second == TaskState.DONE

    # Agent should be cleaned up after success
    assert "task1" not in worker._failed_task_agents

    # Verify first attempt context is still in the agent's memory
    restored_contents = [
        record.memory_record.message.content
        for record in agent.memory.retrieve()
    ]
    assert "first attempt context" in restored_contents

    # Verify retry context message was injected
    retry_messages = [
        record
        for record in agent.memory.retrieve()
        if (record.memory_record.message.meta_dict or {}).get("type")
        == "retry_context"
    ]
    assert len(retry_messages) == 1


@pytest.mark.asyncio
async def test_retry_context_not_duplicated_on_multiple_retries():
    """Verify retry_context messages don't accumulate across retries."""
    sys_msg = BaseMessage.make_assistant_message(
        role_name="tester",
        content="You are a test agent.",
    )

    agent = ChatAgent(sys_msg)
    call_count = 0

    async def astep_toggle(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        response = MagicMock()
        if call_count <= 2:
            response.msg = MagicMock(
                parsed=TaskResult(content="failed", failed=True),
                content='{"content":"failed","failed":true}',
            )
        else:
            response.msg = MagicMock(
                parsed=TaskResult(content="ok", failed=False),
                content='{"content":"ok","failed":false}',
            )
        response.info = {}
        return response

    agent.astep = astep_toggle

    worker = SingleAgentWorker(
        "stub",
        agent,
        use_agent_pool=False,
        enable_breakpoint_resume=True,
        use_structured_output_handler=False,
    )

    first_call = True

    async def get_agent():
        nonlocal first_call
        if first_call:
            first_call = False
            return agent
        raise AssertionError(
            "Should reuse retained agent, not request a new one"
        )

    async def return_agent(a):
        pass

    worker._get_worker_agent = get_agent
    worker._return_worker_agent = return_agent

    task = Task(content="do something", id="task1")

    # First attempt fails
    await worker._process_task(task, [])
    assert "task1" in worker._failed_task_agents

    # Second attempt fails
    task.failure_count = 1
    await worker._process_task(task, [])
    assert "task1" in worker._failed_task_agents

    # Third attempt succeeds
    task.failure_count = 2
    state = await worker._process_task(task, [])
    assert state == TaskState.DONE

    # Check that retry_context messages exist (one per retry)
    retry_messages = [
        record
        for record in agent.memory.retrieve()
        if (record.memory_record.message.meta_dict or {}).get("type")
        == "retry_context"
    ]
    # Two retries = two retry context messages
    assert len(retry_messages) == 2


@pytest.mark.asyncio
async def test_breakpoint_resume_disabled():
    """Verify agent is not retained when feature is disabled."""
    sys_msg = BaseMessage.make_assistant_message(
        role_name="tester",
        content="You are a test agent.",
    )

    agent_first = ChatAgent(sys_msg)
    agent_second = ChatAgent(sys_msg)

    async def astep_fail(*_args, **_kwargs):
        agent_first.update_memory(
            BaseMessage.make_user_message(
                role_name="user", content="first attempt context"
            ),
            OpenAIBackendRole.USER,
        )
        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(content="failed", failed=True),
            content='{"content":"failed","failed":true}',
        )
        response.info = {}
        return response

    async def astep_success(*_args, **_kwargs):
        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(content="ok", failed=False),
            content='{"content":"ok","failed":false}',
        )
        response.info = {}
        return response

    agent_first.astep = astep_fail
    agent_second.astep = astep_success

    # Create worker with breakpoint resume DISABLED
    worker = SingleAgentWorker(
        "stub",
        agent_first,
        use_agent_pool=False,
        enable_breakpoint_resume=False,
        use_structured_output_handler=False,
    )
    # Override to use our test agents
    agents = [agent_first, agent_second]

    async def get_agent():
        return agents.pop(0)

    async def return_agent(agent):
        pass

    worker._get_worker_agent = get_agent
    worker._return_worker_agent = return_agent

    task = Task(content="do something", id="task1")

    # First attempt fails
    state_first = await worker._process_task(task, [])
    assert state_first == TaskState.FAILED

    # No agent should be retained
    assert "task1" not in worker._failed_task_agents

    # Second attempt succeeds (uses a fresh agent)
    task.failure_count = 1
    state_second = await worker._process_task(task, [])
    assert state_second == TaskState.DONE

    # Verify "first attempt context" was NOT in agent_second
    restored_contents = [
        record.memory_record.message.content
        for record in agent_second.memory.retrieve()
    ]
    assert "first attempt context" not in restored_contents
