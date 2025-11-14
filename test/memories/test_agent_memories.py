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
from unittest.mock import MagicMock

import pytest

from camel.memories import (
    BaseContextCreator,
    ChatHistoryBlock,
    ChatHistoryMemory,
    LongtermAgentMemory,
    MemoryRecord,
    VectorDBBlock,
)
from camel.messages import BaseMessage, FunctionCallingMessage
from camel.storages.key_value_storages import InMemoryKeyValueStorage
from camel.types import OpenAIBackendRole, RoleType


class TestLongtermAgentMemory:
    @pytest.fixture
    def mock_chat_history_block(self):
        return MagicMock(spec=ChatHistoryBlock)

    @pytest.fixture
    def mock_vector_db_block(self):
        return MagicMock(spec=VectorDBBlock)

    @pytest.fixture
    def mock_context_creator(self):
        return MagicMock(spec=BaseContextCreator)

    def test_init_with_default_components(self, mock_context_creator):
        memory = LongtermAgentMemory(mock_context_creator)
        assert memory.chat_history_block is not None
        assert memory.vector_db_block is not None

    def test_init_with_custom_components(
        self,
        mock_chat_history_block,
        mock_vector_db_block,
        mock_context_creator,
    ):
        memory = LongtermAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            vector_db_block=mock_vector_db_block,
        )
        assert memory.chat_history_block == mock_chat_history_block
        assert memory.vector_db_block == mock_vector_db_block

    def test_retrieve(
        self,
        mock_chat_history_block,
        mock_vector_db_block,
        mock_context_creator,
    ):
        mock_chat_history_block.retrieve.return_value = ["chat_history_record"]
        mock_vector_db_block.retrieve.return_value = ["vector_db_record"]
        memory = LongtermAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            vector_db_block=mock_vector_db_block,
        )

        records = memory.retrieve()
        assert records == ["chat_history_record", "vector_db_record"]

    def test_write_records(
        self,
        mock_chat_history_block,
        mock_vector_db_block,
        mock_context_creator,
    ):
        memory = LongtermAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            vector_db_block=mock_vector_db_block,
        )
        records = [
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

        memory.write_records(records)
        mock_chat_history_block.write_records.assert_called_once_with(records)
        mock_vector_db_block.write_records.assert_called_once_with(records)
        assert memory._current_topic == "test message 4"

    def test_clear(
        self,
        mock_chat_history_block,
        mock_vector_db_block,
        mock_context_creator,
    ):
        memory = LongtermAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            vector_db_block=mock_vector_db_block,
        )
        memory.clear()
        mock_chat_history_block.clear.assert_called_once()
        mock_vector_db_block.clear.assert_called_once()


class TestChatHistoryMemoryCleanToolCalls:
    @pytest.fixture
    def mock_context_creator(self):
        creator = MagicMock(spec=BaseContextCreator)
        creator.create_context.return_value = ([], 0)
        return creator

    def test_clean_tool_calls_removes_function_messages(
        self, mock_context_creator
    ):
        r"""Test that clean_tool_calls removes FUNCTION role messages."""
        storage = InMemoryKeyValueStorage()
        memory = ChatHistoryMemory(mock_context_creator, storage=storage)

        # Create records with FUNCTION messages
        records = [
            MemoryRecord(
                message=BaseMessage("user", RoleType.USER, None, "Question"),
                role_at_backend=OpenAIBackendRole.USER,
            ),
            MemoryRecord(
                message=FunctionCallingMessage(
                    "assistant",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="tool",
                    result="result",
                ),
                role_at_backend=OpenAIBackendRole.FUNCTION,
            ),
        ]
        memory.write_records(records)

        memory.clean_tool_calls()
        remaining = memory.retrieve()

        assert len(remaining) == 1
        assert (
            remaining[0].memory_record.role_at_backend
            == OpenAIBackendRole.USER
        )

    def test_clean_tool_calls_removes_assistant_with_tool_calls(
        self, mock_context_creator
    ):
        r"""Test that clean_tool_calls removes ASSISTANT messages with tool
        calls.
        """
        storage = InMemoryKeyValueStorage()
        memory = ChatHistoryMemory(mock_context_creator, storage=storage)

        records = [
            MemoryRecord(
                message=BaseMessage("user", RoleType.USER, None, "Question"),
                role_at_backend=OpenAIBackendRole.USER,
            ),
            # Assistant with tool call (has args)
            MemoryRecord(
                message=FunctionCallingMessage(
                    "assistant",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="add",
                    args={"a": 1, "b": 2},
                    tool_call_id="call_123",
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            # Function result
            MemoryRecord(
                message=FunctionCallingMessage(
                    "function",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="add",
                    result="3",
                    tool_call_id="call_123",
                ),
                role_at_backend=OpenAIBackendRole.FUNCTION,
            ),
            # Final assistant response (should be kept)
            MemoryRecord(
                message=BaseMessage(
                    "assistant", RoleType.ASSISTANT, None, "Answer"
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
        ]
        memory.write_records(records)

        memory.clean_tool_calls()
        remaining = memory.retrieve()

        # Should only have USER and final ASSISTANT
        assert len(remaining) == 2
        assert (
            remaining[0].memory_record.role_at_backend
            == OpenAIBackendRole.USER
        )
        assert (
            remaining[1].memory_record.role_at_backend
            == OpenAIBackendRole.ASSISTANT
        )
        assert remaining[1].memory_record.message.content == "Answer"

    def test_clean_tool_calls_handles_multiple_tool_calls(
        self, mock_context_creator
    ):
        r"""Test clean_tool_calls with multiple tool call sequences."""
        storage = InMemoryKeyValueStorage()
        memory = ChatHistoryMemory(mock_context_creator, storage=storage)

        records = [
            MemoryRecord(
                message=BaseMessage("user", RoleType.USER, None, "Q1"),
                role_at_backend=OpenAIBackendRole.USER,
            ),
            MemoryRecord(
                message=FunctionCallingMessage(
                    "assistant",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="tool1",
                    args={"x": 1},
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            MemoryRecord(
                message=FunctionCallingMessage(
                    "function",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="tool1",
                    result="R1",
                ),
                role_at_backend=OpenAIBackendRole.FUNCTION,
            ),
            MemoryRecord(
                message=BaseMessage(
                    "assistant", RoleType.ASSISTANT, None, "A1"
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            MemoryRecord(
                message=BaseMessage("user", RoleType.USER, None, "Q2"),
                role_at_backend=OpenAIBackendRole.USER,
            ),
            MemoryRecord(
                message=FunctionCallingMessage(
                    "assistant",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="tool2",
                    args={"y": 2},
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            MemoryRecord(
                message=FunctionCallingMessage(
                    "function",
                    RoleType.ASSISTANT,
                    None,
                    "",
                    func_name="tool2",
                    result="R2",
                ),
                role_at_backend=OpenAIBackendRole.FUNCTION,
            ),
            MemoryRecord(
                message=BaseMessage(
                    "assistant", RoleType.ASSISTANT, None, "A2"
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
        ]
        memory.write_records(records)

        memory.clean_tool_calls()
        remaining = memory.retrieve()

        # Should only have: USER, ASSISTANT, USER, ASSISTANT
        assert len(remaining) == 4
        expected_roles = [
            OpenAIBackendRole.USER,
            OpenAIBackendRole.ASSISTANT,
            OpenAIBackendRole.USER,
            OpenAIBackendRole.ASSISTANT,
        ]
        actual_roles = [r.memory_record.role_at_backend for r in remaining]
        assert actual_roles == expected_roles
