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

from camel.storages import MemantoStorage  # type: ignore[import-not-found]
from camel.types import OpenAIBackendRole


@pytest.fixture
def mock_memanto_client():
    mock_memanto_module = MagicMock()
    mock_client = MagicMock()
    mock_memanto_module.Memanto.return_value = mock_client

    with patch.dict(sys.modules, {"memanto": mock_memanto_module}):
        yield mock_client


def test_memanto_storage_init(mock_memanto_client):
    storage = MemantoStorage(agent_id="test_agent", api_key="fake_key")
    assert storage.agent_id == "test_agent"
    assert storage.api_key == "fake_key"


def test_memanto_storage_save(mock_memanto_client):
    storage = MemantoStorage(agent_id="test_agent", api_key="fake_key")
    records = [
        {
            "message": {"content": "Hello Memanto"},
            "role_at_backend": OpenAIBackendRole.USER,
        }
    ]
    storage.save(records)
    mock_memanto_client.remember.assert_called_once_with(
        agent_id="test_agent",
        content="Hello Memanto",
        role="user",
    )


def test_memanto_storage_load(mock_memanto_client):
    mock_memanto_client.recall_recent.return_value = [
        {"id": "12345678-1234-5678-1234-567812345678", "content": "Hello back"}
    ]
    storage = MemantoStorage(agent_id="test_agent", api_key="fake_key")
    loaded = storage.load()
    assert len(loaded) == 1
    mock_memanto_client.recall_recent.assert_called_once_with(
        agent_id="test_agent"
    )


def test_memanto_storage_clear(mock_memanto_client):
    storage = MemantoStorage(agent_id="test_agent", api_key="fake_key")
    storage.clear()
    mock_memanto_client.clear.assert_called_once_with(agent_id="test_agent")
