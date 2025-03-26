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
from unittest.mock import MagicMock

import pytest

from camel.memories import GraphDBMemory, MemoryRecord
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole, RoleType


# Fixture to set up GraphDBMemory with mocked dependencies
@pytest.fixture
def graph_db_memory():
    mock_graph_db_block = MagicMock()
    mock_context_creator = MagicMock()
    memory = GraphDBMemory(
        context_creator=mock_context_creator,
        graph_db_block=mock_graph_db_block,
        retrieve_limit=5,
        agent_id="test_agent",
    )
    return memory, mock_graph_db_block, mock_context_creator


# Test initialization of GraphDBMemory
def test_initialization(graph_db_memory):
    memory, mock_graph_db_block, mock_context_creator = graph_db_memory
    assert memory._graph_db_block == mock_graph_db_block
    assert memory._context_creator == mock_context_creator
    assert memory._retrieve_limit == 5
    assert memory.agent_id == "test_agent"


# Test writing records with user and assistant messages
def test_write_records(graph_db_memory):
    memory, mock_graph_db_block, _ = graph_db_memory
    user_record = MemoryRecord(
        message=BaseMessage("user", RoleType.USER, None, "Hello"),
        role_at_backend=OpenAIBackendRole.USER,
        agent_id="",
    )
    assistant_record = MemoryRecord(
        message=BaseMessage("assistant", RoleType.ASSISTANT, None, "Hi"),
        role_at_backend=OpenAIBackendRole.ASSISTANT,
        agent_id="test_agent",
    )
    records = [user_record, assistant_record]
    memory.write_records(records)
    assert user_record.agent_id == "test_agent"  # Updated from empty
    assert assistant_record.agent_id == "test_agent"  # Unchanged
    assert memory._current_query == "Hello"  # Updated to user message
    mock_graph_db_block.write_records.assert_called_once_with(records)


# Test writing records without a user message
def test_write_records_no_user(graph_db_memory):
    memory, mock_graph_db_block, _ = graph_db_memory
    memory._current_query = None
    assistant_record = MemoryRecord(
        message=BaseMessage("assistant", RoleType.ASSISTANT, None, "Hi"),
        role_at_backend=OpenAIBackendRole.ASSISTANT,
        agent_id="test_agent",
    )
    memory.write_records([assistant_record])
    assert memory._current_query is None  # Should not update
    mock_graph_db_block.write_records.assert_called_once_with(
        [assistant_record]
    )


# Test retrieving records with a query
def test_retrieve_with_query(graph_db_memory):
    memory, mock_graph_db_block, _ = graph_db_memory
    memory._current_query = "test query"
    mock_context_record = MagicMock()
    mock_graph_db_block.retrieve.return_value = [mock_context_record]
    records = memory.retrieve()
    mock_graph_db_block.retrieve.assert_called_once_with(
        query="test query", numberOfNearestNeighbours=5
    )
    assert records == [mock_context_record]


# Test retrieving records without a query
def test_retrieve_without_query(graph_db_memory):
    memory, mock_graph_db_block, _ = graph_db_memory
    memory._current_query = None
    mock_context_record = MagicMock()
    mock_graph_db_block.retrieve.return_value = [mock_context_record]
    records = memory.retrieve()
    mock_graph_db_block.retrieve.assert_called_once_with(
        query=None, numberOfNearestNeighbours=5
    )
    assert records == [mock_context_record]


# Test clearing the memory
def test_clear(graph_db_memory):
    memory, mock_graph_db_block, _ = graph_db_memory
    memory.clear()
    mock_graph_db_block.clear.assert_called_once()


# Test setting and getting agent_id
def test_agent_id(graph_db_memory):
    memory, _, _ = graph_db_memory
    assert memory.agent_id == "test_agent"
    memory.agent_id = "new_agent"
    assert memory.agent_id == "new_agent"
