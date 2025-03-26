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
from datetime import datetime
from unittest.mock import MagicMock, create_autospec, patch
from uuid import uuid4

import pytest

from camel.embeddings import BaseEmbedding
from camel.memories import (
    ChatHistoryBlock,
    ContextRecord,
    GraphDBBlock,
    MemoryRecord,
    VectorDBBlock,
)
from camel.messages import BaseMessage
from camel.storages import (
    BaseGraphStorage,
    BaseKeyValueStorage,
    BaseVectorStorage,
    GraphElement,
    VectorDBQueryResult,
)
from camel.types import OpenAIBackendRole, RoleType


def generate_mock_records(num_records: int):
    return [
        {
            "uuid": str(uuid4()),
            "message": {
                "__class__": "BaseMessage",
                "role_name": "user",
                "role_type": RoleType.USER,
                "meta_dict": None,
                "content": f"test message {i}",
            },
            "role_at_backend": "user",
            "extra_info": {},
            "timestamp": datetime.now().timestamp(),
            "agent_id": f"test_agent_{i}",
        }
        for i in range(num_records)
    ]


class TestChatHistoryBlock:
    @pytest.fixture
    def mock_storage(self):
        return create_autospec(BaseKeyValueStorage)

    def test_init_with_default_storage(self):
        chat_history = ChatHistoryBlock()
        assert chat_history.storage is not None

    def test_init_with_custom_storage(self, mock_storage):
        chat_history = ChatHistoryBlock(storage=mock_storage)
        assert chat_history.storage == mock_storage

    def test_retrieve_with_window_size(self, mock_storage):
        mock_records = generate_mock_records(10)
        mock_storage.load.return_value = mock_records
        chat_history = ChatHistoryBlock(storage=mock_storage)

        records = chat_history.retrieve(window_size=5)
        assert all(isinstance(record, ContextRecord) for record in records)
        assert len(records) == 5

    def test_retrieve_without_window_size(self, mock_storage):
        mock_records = generate_mock_records(10)
        mock_storage.load.return_value = mock_records
        chat_history = ChatHistoryBlock(storage=mock_storage)

        records = chat_history.retrieve()
        assert all(isinstance(record, ContextRecord) for record in records)
        assert len(records) == 10

    def test_retrieve_empty_history(self, mock_storage):
        mock_storage.load.return_value = []
        chat_history = ChatHistoryBlock(storage=mock_storage)

        records = chat_history.retrieve()
        assert records == []

    def test_write_records(self, mock_storage):
        chat_history = ChatHistoryBlock(storage=mock_storage)
        records_to_write = [
            MemoryRecord(
                message=BaseMessage(
                    "user",
                    RoleType.USER,
                    None,
                    "test message {}".format(i),
                ),
                role_at_backend=OpenAIBackendRole.USER,
                timestamp=datetime.now().timestamp(),
                agent_id=f"test_agent_{i}",
            )
            for i in range(5)
        ]

        chat_history.write_records(records_to_write)
        mock_storage.save.assert_called_once()

    def test_clear_history(self, mock_storage):
        chat_history = ChatHistoryBlock(storage=mock_storage)
        chat_history.clear()
        mock_storage.clear.assert_called_once()


class TestVectorDBBlock:
    @pytest.fixture
    def mock_storage(self):
        return create_autospec(BaseVectorStorage)

    @pytest.fixture
    def mock_embedding(self):
        mock = MagicMock(spec=BaseEmbedding)
        mock.get_output_dim.return_value = 128
        mock.embed.return_value = [0.1] * 128  # Example vector representation
        return mock

    def test_init_with_default_components(self):
        vector_db = VectorDBBlock()
        assert vector_db.storage is not None
        assert vector_db.embedding is not None

    def test_init_with_custom_components(self, mock_storage, mock_embedding):
        vector_db = VectorDBBlock(
            storage=mock_storage, embedding=mock_embedding
        )
        assert vector_db.storage == mock_storage
        assert vector_db.embedding == mock_embedding

    def test_retrieve(self, mock_storage, mock_embedding):
        # Generate mock records
        mock_records = generate_mock_records(2)

        # Create VectorDBQueryResult list using mock_records
        mock_query_results = [
            VectorDBQueryResult.create(
                similarity=0.9,
                vector=[0.1] * 128,  # Example vector
                id=record["uuid"],
                payload=record,
            )
            for record in mock_records
        ]
        mock_storage.query.return_value = mock_query_results
        vector_db = VectorDBBlock(
            storage=mock_storage, embedding=mock_embedding
        )

        records = vector_db.retrieve("keyword", limit=2)
        assert len(records) == 2
        assert all(isinstance(record, ContextRecord) for record in records)
        assert records[0].memory_record.message.content == "test message 0"
        assert records[1].memory_record.message.content == "test message 1"

    def test_write_records(self, mock_storage, mock_embedding):
        vector_db = VectorDBBlock(
            storage=mock_storage, embedding=mock_embedding
        )
        records_to_write = [
            MemoryRecord(
                message=BaseMessage(
                    "user",
                    RoleType.USER,
                    None,
                    "test message {}".format(i),
                ),
                role_at_backend=OpenAIBackendRole.USER,
                timestamp=datetime.now().timestamp(),
                agent_id=f"test_agent_{i}",
            )
            for i in range(5)
        ]

        vector_db.write_records(records_to_write)
        mock_storage.add.assert_called_once()

    def test_clear_history(self, mock_storage):
        vector_db = VectorDBBlock(storage=mock_storage)
        vector_db.clear()
        mock_storage.clear.assert_called_once()


class TestGraphElement(GraphElement):
    def __init__(self):
        self.nodes = []


class TestGraphDBBlock:
    @pytest.fixture
    def mock_storage(self):
        """Fixture to provide a mock BaseGraphStorage object."""
        return create_autospec(BaseGraphStorage)

    @pytest.fixture
    def mock_embedding(self):
        """Fixture to provide a mock BaseEmbedding object."""
        mock = MagicMock(spec=BaseEmbedding)
        mock.embed.return_value = [
            0.1
        ] * 1536  # Assuming 1536-dimensional embedding
        return mock

    def test_init_with_custom_components(self, mock_storage, mock_embedding):
        """Test initialization with custom storage and embedding components."""
        block = GraphDBBlock(storage=mock_storage, embedding=mock_embedding)
        assert block.storage == mock_storage
        assert block.embedding == mock_embedding

    def test_retrieve_with_query(self, mock_storage, mock_embedding):
        """Test retrieving records with a query using similarity search."""
        flat_dict = {
            "uuid": str(uuid4()),
            "message___class__": "BaseMessage",
            "message_role_name": "user",
            "message_role_type": "USER",
            "message_content": "test message",
            "role_at_backend": "user",
            "timestamp": datetime.now().timestamp(),
            "agent_id": "test_agent",
        }
        query_result = [{"n": flat_dict, "similarity": 0.9}]
        mock_storage.query.return_value = query_result

        block = GraphDBBlock(storage=mock_storage, embedding=mock_embedding)
        records = block.retrieve(
            query="test query", numberOfNearestNeighbours=1
        )

        assert len(records) == 1
        assert isinstance(records[0], ContextRecord)
        assert records[0].memory_record.message.content == "test message"
        assert records[0].score == 0.9

    def test_retrieve_without_query(self, mock_storage):
        """Test retrieving recent records without a query."""
        flat_dict = {
            "uuid": str(uuid4()),
            "message___class__": "BaseMessage",
            "message_role_name": "user",
            "message_role_type": "USER",
            "message_content": "test message",
            "role_at_backend": "user",
            "timestamp": datetime.now().timestamp(),
            "agent_id": "test_agent",
        }
        query_result = [{"n": flat_dict}]
        mock_storage.query.return_value = query_result

        block = GraphDBBlock(storage=mock_storage)
        records = block.retrieve(numberOfNearestNeighbours=1)

        assert len(records) == 1
        assert isinstance(records[0], ContextRecord)
        assert records[0].memory_record.message.content == "test message"
        assert records[0].score == 0

    @patch('camel.agents.KnowledgeGraphAgent')
    def test_write_records(self, mock_kg_agent, mock_storage, mock_embedding):
        """Test writing records to the graph database."""
        # Create a mock GraphElement instance using create_autospec
        mock_graph_element = create_autospec(GraphElement)
        mock_graph_element.nodes = []  # Set the nodes attribute as needed
        mock_kg_agent.return_value.run.return_value = mock_graph_element

        # Initialize the GraphDBBlock with mocked dependencies
        block = GraphDBBlock(storage=mock_storage, embedding=mock_embedding)
        record = MemoryRecord(
            message=BaseMessage("user", RoleType.USER, None, "test message"),
            role_at_backend=OpenAIBackendRole.USER,
        )

        # Execute the method under test
        block.write_records([record])

        # Verify expected interactions
        mock_storage.add_graph_elements.assert_called_once()
        mock_storage.query.assert_called()

    @patch.object(MemoryRecord, 'to_dict')
    def test_delete_records(self, mock_to_dict, mock_storage):
        """Test deleting specific records by UUID."""
        mock_to_dict.return_value = {"uuid": "some-uuid"}

        block = GraphDBBlock(storage=mock_storage)
        record = MemoryRecord(
            message=BaseMessage("user", RoleType.USER, None, "test message"),
            role_at_backend=OpenAIBackendRole.USER,
        )

        block.delete_records([record])

        mock_storage.query.assert_called_with(
            "MATCH (m:Message {uuid: $uuid}) DETACH DELETE m",
            {"uuid": "some-uuid"},
        )

    def test_clear(self, mock_storage):
        """Test clearing all records from the graph database."""
        block = GraphDBBlock(storage=mock_storage)
        block.clear()
        mock_storage.query.assert_called_with("MATCH (n) DETACH DELETE n")
