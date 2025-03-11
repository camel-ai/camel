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
import json
import pytest
from unittest.mock import MagicMock

from camel.toolkits.memory_toolkit import MemoryToolkit

@pytest.fixture(scope="function")
def memory_toolkit_fixture():
    mock_agent = MagicMock()
    mock_agent.model_backend.token_counter = MagicMock()
    mock_agent.model_backend.token_limit = 1000
    toolkit = MemoryToolkit(agent=mock_agent)
    return toolkit

def test_save_memory(memory_toolkit_fixture):
    toolkit = memory_toolkit_fixture
    path = "test_memory.json"

    toolkit.agent.save_memory.return_value = f"Memory saved to {path}"
    result = toolkit.save(path)

    assert "Memory saved to" in result

def test_load_memory_valid_json(memory_toolkit_fixture):
    toolkit = memory_toolkit_fixture
    memory_json = json.dumps([{"message": {"content": "hello", "role": "user"}, 
                "role_at_backend": "user", "agent_id": "test_agent"}])

    # Mocking the memory loading process properly
    mock_memory = MagicMock()
    toolkit.agent.load_memory.return_value = None  # Simulate a successful load
    result = toolkit.load(memory_json)

def test_load_memory_invalid_json(memory_toolkit_fixture):
    toolkit = memory_toolkit_fixture
    invalid_json = "{invalid json}"

    result = toolkit.load(invalid_json)

    assert "[ERROR] Invalid JSON string provided." in result

def test_load_memory_wrong_format(memory_toolkit_fixture):
    toolkit = memory_toolkit_fixture
    incorrect_json = json.dumps({"not": "a list"})

    result = toolkit.load(incorrect_json)

    assert "[ERROR] Memory data should be a list of records." in result

def test_load_from_path(memory_toolkit_fixture):
    toolkit = memory_toolkit_fixture
    path = "memory.json"

    toolkit.agent.load_memory_from_path.return_value = f"Memory loaded from {path}"
    result = toolkit.load_from_path(path)

    assert "Memory loaded from" in result

def test_clear_memory(memory_toolkit_fixture):
    toolkit = memory_toolkit_fixture

    toolkit.agent.clear_memory.return_value = "Memory has been cleared."
    result = toolkit.clear_memory()

    assert "Memory has been cleared." in result
