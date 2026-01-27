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
from typing import List
from unittest.mock import MagicMock

import pytest

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.utils import TaskResult
from camel.tasks.task import Task, TaskState
from camel.types import OpenAIBackendRole


class _StubWorker(SingleAgentWorker):
    def __init__(self, description: str, agents: List[ChatAgent]):
        super().__init__(
            description,
            agents[0],
            use_agent_pool=False,
            enable_breakpoint_resume=True,
            use_structured_output_handler=False,
        )
        self._agents = list(agents)

    async def _get_worker_agent(self) -> ChatAgent:
        return self._agents.pop(0)

    async def _return_worker_agent(self, agent: ChatAgent) -> None:
        return None


@pytest.mark.asyncio
async def test_breakpoint_resume_restores_history_and_retry_context():
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
            content="{\"content\":\"failed\",\"failed\":true}",
        )
        response.info = {}
        return response

    async def astep_success(*_args, **_kwargs):
        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(content="ok", failed=False),
            content="{\"content\":\"ok\",\"failed\":false}",
        )
        response.info = {}
        return response

    agent_first.astep = astep_fail
    agent_second.astep = astep_success

    worker = _StubWorker("stub", [agent_first, agent_second])
    task = Task(content="do something", id="task1")

    state_first = await worker._process_task(task, [])
    assert state_first == TaskState.FAILED

    history = task.execution_context.get("conversation_history")
    assert history is not None
    assert len(history) >= 1

    task.failure_count = 1
    state_second = await worker._process_task(task, [])
    assert state_second == TaskState.DONE

    retry_context = task.execution_context.get("retry_context")
    assert retry_context

    restored_contents = [
        record.memory_record.message.content
        for record in agent_second.memory.retrieve()
    ]
    assert "first attempt context" in restored_contents
    assert retry_context in restored_contents


@pytest.mark.asyncio
async def test_retry_context_not_duplicated_on_multiple_retries():
    """Verify retry_context messages don't accumulate across retries."""
    sys_msg = BaseMessage.make_assistant_message(
        role_name="tester",
        content="You are a test agent.",
    )

    agent1 = ChatAgent(sys_msg)
    agent2 = ChatAgent(sys_msg)
    agent3 = ChatAgent(sys_msg)

    async def astep_fail(*_args, **_kwargs):
        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(content="failed", failed=True),
            content="{\"content\":\"failed\",\"failed\":true}",
        )
        response.info = {}
        return response

    async def astep_success(*_args, **_kwargs):
        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(content="ok", failed=False),
            content="{\"content\":\"ok\",\"failed\":false}",
        )
        response.info = {}
        return response

    agent1.astep = astep_fail
    agent2.astep = astep_fail
    agent3.astep = astep_success

    worker = _StubWorker("stub", [agent1, agent2, agent3])
    task = Task(content="do something", id="task1")

    # First attempt fails
    await worker._process_task(task, [])
    assert task.execution_context is not None

    # Second attempt fails
    task.failure_count = 1
    await worker._process_task(task, [])

    # Third attempt succeeds
    task.failure_count = 2
    state = await worker._process_task(task, [])
    assert state == TaskState.DONE

    # Check that only ONE retry_context message exists in agent3's memory
    retry_messages = [
        record
        for record in agent3.memory.retrieve()
        if (record.memory_record.message.meta_dict or {}).get("type")
        == "retry_context"
    ]
    assert len(retry_messages) == 1


@pytest.mark.asyncio
async def test_breakpoint_resume_disabled():
    """Verify no history is saved/restored when feature is disabled."""
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
            content="{\"content\":\"failed\",\"failed\":true}",
        )
        response.info = {}
        return response

    async def astep_success(*_args, **_kwargs):
        response = MagicMock()
        response.msg = MagicMock(
            parsed=TaskResult(content="ok", failed=False),
            content="{\"content\":\"ok\",\"failed\":false}",
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

    # execution_context should be None or empty (no history saved)
    assert task.execution_context is None or not task.execution_context.get(
        "conversation_history"
    )

    # Second attempt succeeds
    task.failure_count = 1
    state_second = await worker._process_task(task, [])
    assert state_second == TaskState.DONE

    # Verify "first attempt context" was NOT restored to agent_second
    restored_contents = [
        record.memory_record.message.content
        for record in agent_second.memory.retrieve()
    ]
    assert "first attempt context" not in restored_contents
