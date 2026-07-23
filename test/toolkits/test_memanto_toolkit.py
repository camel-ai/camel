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

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
import pytest

from camel.toolkits.memanto_toolkit import MemantoToolkit

AGENT_ID = "my-camel-agent"
BASE_URL = os.getenv("MEMANTO_BASE_URL", "http://127.0.0.1:8000")


def _memanto_server_available() -> bool:
    try:
        response = httpx.get(f"{BASE_URL.rstrip('/')}/health", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="function")
def memanto_toolkit_fixture():
    mock_client = MagicMock()
    patcher = patch(
        "camel.toolkits.memanto_toolkit.MemantoRESTClient",
        return_value=mock_client,
    )
    patcher.start()
    toolkit = MemantoToolkit(agent_id="test_agent")
    toolkit._client = mock_client
    yield toolkit, mock_client
    patcher.stop()


def test_memanto_remember(memanto_toolkit_fixture):
    toolkit, mock_client = memanto_toolkit_fixture
    mock_client.remember.return_value = "mem-123"

    result = toolkit.memanto_remember(
        content="User prefers Python",
        memory_type="preference",
        tags="language, python",
        confidence=0.9,
    )

    assert "mem-123" in result
    mock_client.remember.assert_called_once_with(
        content="User prefers Python",
        memory_type="preference",
        confidence=0.9,
        tags=["language", "python"],
    )


def test_memanto_recall(memanto_toolkit_fixture):
    toolkit, mock_client = memanto_toolkit_fixture
    mock_client.recall.return_value = [
        {"content": "User prefers Python", "type": "preference"}
    ]

    result = toolkit.memanto_recall(
        query="What language does the user prefer?",
        limit=3,
        memory_type="preference,fact",
    )
    parsed = json.loads(result)

    assert len(parsed) == 1
    mock_client.recall.assert_called_once_with(
        query="What language does the user prefer?",
        limit=3,
        memory_type=["preference", "fact"],
    )


def test_memanto_answer(memanto_toolkit_fixture):
    toolkit, mock_client = memanto_toolkit_fixture
    mock_client.answer.return_value = "The user prefers Python."

    result = toolkit.memanto_answer("What language does the user prefer?")

    assert result == "The user prefers Python."
    mock_client.answer.assert_called_once_with(
        question="What language does the user prefer?"
    )


def test_get_tools(memanto_toolkit_fixture):
    toolkit, _ = memanto_toolkit_fixture
    tools = toolkit.get_tools()
    tool_names = {tool.get_function_name() for tool in tools}

    assert tool_names == {
        "memanto_remember",
        "memanto_recall",
        "memanto_answer",
    }


def test_initialization_requires_agent_id():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError):
            MemantoToolkit()


@pytest.mark.skipif(
    not _memanto_server_available(),
    reason="Memanto server is not running at MEMANTO_BASE_URL",
)
class TestMemantoToolkitIntegration(unittest.TestCase):
    r"""Live integration tests for MemantoToolkit.

    Prerequisites:
        memanto serve
        memanto agent create my-camel-agent
    """

    def setUp(self):
        self.toolkit = MemantoToolkit(
            agent_id=AGENT_ID,
            base_url=BASE_URL,
        )

    def test_remember_and_recall(self):
        remember_result = self.toolkit.memanto_remember(
            content="Integration test user prefers Python over JavaScript.",
            memory_type="preference",
            tags="integration, language",
            confidence=0.95,
        )
        self.assertIn("Memory stored with ID", remember_result)

        recall_result = self.toolkit.memanto_recall(
            query="What programming language does the user prefer?",
            limit=5,
            memory_type="preference",
        )
        self.assertNotIn("[ERROR]", recall_result)
        self.assertIn("Python", recall_result)

    def test_answer(self):
        self.toolkit.memanto_remember(
            content="The user's name is Alex and they work in finance.",
            memory_type="fact",
            confidence=1.0,
        )

        answer = self.toolkit.memanto_answer(
            "What industry does the user work in?"
        )
        self.assertNotIn("[ERROR]", answer)
        self.assertTrue(len(answer.strip()) > 0)
