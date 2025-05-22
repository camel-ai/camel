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
from unittest.mock import Mock, patch

import pytest
from mcp.server.fastmcp import Context

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.societies.workforce import Workforce
from camel.tasks.task import Task, TaskState
from services.workforce_mcp.server import (
    add_single_agent_worker,
    get_workforce_info,
    process_task,
    reset_workforce,
)


@pytest.fixture
def mock_workforce():
    workforce = Mock(spec=Workforce)
    workforce.node_id = "test_workforce"
    workforce._get_child_nodes_info.return_value = (
        "Test Worker: tools: thinking, code"
    )
    workforce.process_task.return_value = Mock(spec=Task)
    workforce.add_single_agent_worker.return_value = workforce
    workforce.reset.return_value = None
    return workforce


@pytest.fixture
def mock_context():
    context = Mock(spec=Context)
    context.info = Mock()
    return context


@pytest.fixture
def mock_task():
    task = Mock(spec=Task)
    task.id = "test_task"
    task.content = "Test task content"
    task.additional_info = "Test additional info"
    task.state = TaskState.DONE
    return task


@pytest.fixture
def mock_message():
    message = Mock(spec=BaseMessage)
    message.to_dict.return_value = {
        "role": "assistant",
        "content": "Test response",
    }
    return message


@pytest.fixture
def mock_agent():
    agent = Mock(spec=ChatAgent)
    agent.tool_dict = {"thinking": None, "code": None}
    return agent


@pytest.mark.asyncio
async def test_get_workforce_info_success(mock_workforce, mock_context):
    with patch("services.workforce_mcp.server.workforce", mock_workforce):
        mock_workforce._children = []
        mock_workforce.node_id = "test_id"
        mock_workforce.description = "test description"
        result = get_workforce_info()
        assert isinstance(result, dict)
        assert "id" in result
        assert "description" in result
        assert "children" in result


@pytest.mark.asyncio
async def test_add_single_agent_worker_success(
    mock_workforce, mock_context, mock_agent
):
    with (
        patch("services.workforce_mcp.server.workforce", mock_workforce),
        patch("services.workforce_mcp.server.ChatAgent") as mock_chat_agent,
    ):
        mock_chat_agent.return_value = mock_agent
        mock_workforce._children = []
        mock_child = Mock()
        mock_child.node_id = "test_child_id"
        mock_workforce._children.append(mock_child)

        result = add_single_agent_worker(
            description="Test Worker",
            system_message="You are a test worker.",
            model_name=None,
            tools=["thinking", "code"],
            ctx=mock_context,
        )
        assert result["status"] == "success"
        assert "message" in result
        mock_workforce.add_single_agent_worker.assert_called_once()


@pytest.mark.asyncio
async def test_process_task_success(mock_workforce, mock_context, mock_task):
    with patch("services.workforce_mcp.server.workforce", mock_workforce):
        mock_task.id = "test_id"
        mock_task.content = "test content"
        mock_task.result = "test result"
        mock_state = Mock()
        mock_state.name = "DONE"
        mock_task.state = mock_state
        mock_task.subtasks = []
        mock_workforce.process_task.return_value = mock_task

        result = process_task(
            "Test task content",
            "Test additional info",
            mock_context,
        )
        assert result["status"] == "success"
        assert result["task_id"] == "test_id"
        mock_workforce.process_task.assert_called_once()


@pytest.mark.asyncio
async def test_process_task_failure(mock_workforce, mock_context, mock_task):
    with patch("services.workforce_mcp.server.workforce", mock_workforce):
        mock_task.id = "test_id"
        mock_task.content = "test content"
        mock_task.result = "test result"
        mock_state = Mock()
        mock_state.name = "FAILED"
        mock_task.state = mock_state
        mock_task.subtasks = []
        mock_workforce.process_task.return_value = mock_task

        result = process_task(
            "Test task content",
            "Test additional info",
            mock_context,
        )
        assert result["status"] == "failed"
        mock_workforce.process_task.assert_called_once()


def test_reset_workforce_success(mock_workforce, mock_context):
    with patch("services.workforce_mcp.server.workforce", mock_workforce):
        result = reset_workforce(mock_context)

        assert result["status"] == "success"
        assert "successfully" in result["message"]
        mock_workforce.reset.assert_called_once()
        mock_context.info.assert_called_once()
