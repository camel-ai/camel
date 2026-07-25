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

import sys
from unittest.mock import MagicMock, patch

import pytest  # type: ignore[import-not-found]

from camel.toolkits import MemantoToolkit


@pytest.fixture
def mock_memanto_client():
    mock_memanto_module = MagicMock()
    mock_client = MagicMock()
    mock_memanto_module.Memanto.return_value = mock_client

    with patch.dict(sys.modules, {"memanto": mock_memanto_module}):
        yield mock_client


def test_memanto_toolkit_get_tools(mock_memanto_client):
    toolkit = MemantoToolkit(agent_id="test_agent", api_key="fake_key")
    tools = toolkit.get_tools()
    assert len(tools) == 3


def test_memanto_remember_tool(mock_memanto_client):
    mock_memanto_client.remember.return_value = "mem_123"
    toolkit = MemantoToolkit(agent_id="test_agent", api_key="fake_key")
    res = toolkit.memanto_remember(content="test memory", type="fact")
    assert "mem_123" in res
    mock_memanto_client.remember.assert_called_once()


def test_memanto_recall_tool(mock_memanto_client):
    mock_memanto_client.recall.return_value = ["memory 1"]
    toolkit = MemantoToolkit(agent_id="test_agent", api_key="fake_key")
    res = toolkit.memanto_recall(query="test query")
    assert "memory 1" in res
    mock_memanto_client.recall.assert_called_once()


def test_memanto_answer_tool(mock_memanto_client):
    mock_memanto_client.answer.return_value = "Grounded answer"
    toolkit = MemantoToolkit(agent_id="test_agent", api_key="fake_key")
    res = toolkit.memanto_answer(question="What is X?")
    assert "Grounded answer" in res
    mock_memanto_client.answer.assert_called_once()
