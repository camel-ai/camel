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
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task


@pytest.mark.asyncio
async def test_get_dep_tasks_info():
    sys_msg = BaseMessage.make_assistant_message(
        role_name="programmer",
        content="You are a python programmer.",
    )
    agent = ChatAgent(sys_msg)
    test_worker = SingleAgentWorker('agent1', agent)
    human_task = Task(
        content='develop a python program of investing stock.',
        id='0',
    )

    subtasks = human_task.decompose(agent)  # TODO: use MagicMock
    await test_worker._process_task(
        human_task, subtasks
    )  # TODO: use MagicMock


@pytest.mark.asyncio
async def test_task_sequence_workforce():
    """Tests that the Workforce correctly processes a sequence of tasks
    and propagates results to the shared context."""

    sys_msg = BaseMessage.make_assistant_message(
        role_name="researcher",
        content="You are a researcher who can analyze projects.",
    )

    researcher_agent = ChatAgent(sys_msg)

    mock_agent = MagicMock()
    mock_agent.step = AsyncMock(return_value=("Score: 8/10", None))

    workforce = Workforce("Review Committee")
    workforce.add_single_agent_worker("Researcher", researcher_agent)
    workforce.add_single_agent_worker("Judge A", mock_agent)
    workforce.add_single_agent_worker("Judge B", mock_agent)

    original_start = workforce.start

    async def mock_start():
        if workforce._task:
            workforce._task.result = (
                f"Processed result: " f"{workforce._task.content}"
            )

    workforce.start = AsyncMock(side_effect=mock_start)
    workforce._decompose_task = MagicMock(return_value=[])

    task_list = [
        Task(
            id="research",
            content="Conduct brief research on the test project. Summarize "
            "core ideas, technology used, and potential impact.",
        ),
        Task(
            id="judge_A",
            content="As Judge A, review the project based on the research "
            "summary. Provide feedback and score from 1 to 10.",
        ),
        Task(
            id="judge_B",
            content="As Judge B, evaluate the project using your own "
            "criteria. Based on research, provide critique and score "
            "from 1 to 10.",
        ),
    ]

    results = await workforce.process_task_sequence_async(task_list)

    assert len(results) == 3
    assert all(task.result is not None for task in results)
    assert "task_research" in workforce.shared_context
    assert "task_judge_A" in workforce.shared_context
    assert "task_judge_B" in workforce.shared_context

    for task in results:
        assert (
            workforce.shared_context[f"task_{task.id}"]["result"]
            == f"Processed result: {task.content}"
        )
        assert (
            workforce.shared_context[f"task_{task.id}"]["content"]
            == task.content
        )

    single_task = Task(id="test_task", content="Content that needs processing")

    workforce.shared_context.clear()

    single_result = await workforce.process_task_sequence_async([single_task])

    assert (
        single_result[0].result
        == "Processed result: Content that needs processing"
    )
    assert (
        workforce.shared_context["task_test_task"]["result"]
        == "Processed result: Content that needs processing"
    )
    assert (
        workforce.shared_context["task_test_task"]["content"]
        == "Content that needs processing"
    )

    workforce.start = original_start
