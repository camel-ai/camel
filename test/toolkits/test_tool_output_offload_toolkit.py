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
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from camel.toolkits.tool_output_offload_toolkit import (
    OffloadedOutput,
    ToolOutputOffloadToolkit,
)


class TestToolOutputOffloadToolkit:
    r"""Test suite for ToolOutputOffloadToolkit."""

    def test_init_creates_storage_directory(self):
        r"""Test that initialization creates the storage directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            assert toolkit.session_dir.exists()
            assert toolkit.outputs_dir.exists()
            assert toolkit.session_dir.parent == Path(tmp_dir)

    def test_init_with_default_min_length(self):
        r"""Test default min_output_length value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            assert toolkit.min_output_length == 1000

    def test_init_with_custom_min_length(self):
        r"""Test custom min_output_length value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                min_output_length=500,
            )
            assert toolkit.min_output_length == 500

    def test_list_offloadable_outputs_no_agent(self):
        r"""Test listing with no registered agent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.list_offloadable_outputs()

            assert "No tool outputs found" in result
            assert "Total tool outputs in memory: 0" in result

    def test_list_offloadable_outputs_empty_memory(self):
        r"""Test listing with empty memory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Mock agent with empty memory
            mock_agent = MagicMock()
            mock_storage = MagicMock()
            mock_storage.load.return_value = []

            mock_chat_history_block = MagicMock()
            mock_chat_history_block.storage = mock_storage

            mock_memory = MagicMock()
            mock_memory._chat_history_block = mock_chat_history_block

            mock_agent.memory = mock_memory
            toolkit._agent = mock_agent

            result = toolkit.list_offloadable_outputs()

            assert "No tool outputs found" in result

    def test_list_offloadable_outputs_filters_by_length(self):
        r"""Test that outputs below min_length are excluded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                min_output_length=100,
            )

            # Mock agent with tool outputs of varying lengths
            mock_agent = MagicMock()
            mock_storage = MagicMock()
            mock_storage.load.return_value = [
                {
                    "uuid": "uuid-1",
                    "timestamp": 1000,
                    "message": {
                        "__class__": "FunctionCallingMessage",
                        "func_name": "short_tool",
                        "tool_call_id": "call-1",
                        "result": "short",  # 5 chars, below threshold
                    },
                },
                {
                    "uuid": "uuid-2",
                    "timestamp": 2000,
                    "message": {
                        "__class__": "FunctionCallingMessage",
                        "func_name": "long_tool",
                        "tool_call_id": "call-2",
                        "result": "x" * 200,  # 200 chars, above threshold
                    },
                },
            ]

            mock_chat_history_block = MagicMock()
            mock_chat_history_block.storage = mock_storage

            mock_memory = MagicMock()
            mock_memory._chat_history_block = mock_chat_history_block

            mock_agent.memory = mock_memory
            toolkit._agent = mock_agent

            result = toolkit.list_offloadable_outputs()

            assert "long_tool" in result
            assert "short_tool" not in result
            assert "1 offloadable" in result

    def test_summarize_and_offload_no_cached_list(self):
        r"""Test error when no cached list exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.summarize_and_offload(0)

            assert "No offloadable outputs cached" in result
            assert "list_offloadable_outputs()" in result

    def test_summarize_and_offload_invalid_index(self):
        r"""Test error handling for invalid index."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            toolkit._last_offloadable_list = [{"test": "data"}]

            result = toolkit.summarize_and_offload(5)

            assert "Invalid index" in result

    def test_retrieve_offloaded_output_not_found(self):
        r"""Test error handling for missing offload_id."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.retrieve_offloaded_output("nonexistent-id")

            assert "not found" in result
            assert "list_offloaded_outputs()" in result

    def test_retrieve_offloaded_output_success(self):
        r"""Test successful retrieval of offloaded content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Create offloaded content
            offload_id = "test-123"
            original_content = "This is the original content"

            content_file = toolkit.outputs_dir / f"{offload_id}.txt"
            content_file.write_text(original_content)

            meta = OffloadedOutput(
                offload_id=offload_id,
                tool_name="test_tool",
                tool_call_id="call-1",
                record_uuid="uuid-1",
                original_length=len(original_content),
                summary="Test summary",
                file_path=str(content_file),
                timestamp=1000,
                offloaded_at="2024-01-01T00:00:00",
            )
            toolkit._offloaded_outputs[offload_id] = meta

            result = toolkit.retrieve_offloaded_output(offload_id)

            assert original_content in result
            assert "Retrieved Original Content" in result

    def test_list_offloaded_outputs_empty(self):
        r"""Test listing when no outputs have been offloaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.list_offloaded_outputs()

            assert "No outputs have been offloaded" in result

    def test_list_offloaded_outputs_with_data(self):
        r"""Test listing with offloaded outputs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Add offloaded outputs
            toolkit._offloaded_outputs["id-1"] = OffloadedOutput(
                offload_id="id-1",
                tool_name="tool_a",
                tool_call_id="call-1",
                record_uuid="uuid-1",
                original_length=5000,
                summary="Summary of tool A output",
                file_path="/path/to/file",
                timestamp=1000,
                offloaded_at="2024-01-01T00:00:00",
            )

            result = toolkit.list_offloaded_outputs()

            assert "id-1" in result
            assert "tool_a" in result
            assert "5000" in result
            assert "1 total" in result

    def test_get_offload_info(self):
        r"""Test getting offload status info."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.get_offload_info()

            assert "Offloaded outputs: 0" in result
            assert "Storage directory:" in result
            assert "Tool outputs in memory: 0" in result

    def test_get_tools_returns_all_tools(self):
        r"""Test that get_tools returns all expected tools."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            tools = toolkit.get_tools()

            tool_names = [tool.get_function_name() for tool in tools]
            assert "list_offloadable_outputs" in tool_names
            assert "summarize_and_offload" in tool_names
            assert "retrieve_offloaded_output" in tool_names
            assert "list_offloaded_outputs" in tool_names
            assert "get_offload_info" in tool_names
            assert len(tools) == 5

    def test_serialize_result_string(self):
        r"""Test serialization of string result."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit._serialize_result("test string")
            assert result == "test string"

    def test_serialize_result_dict(self):
        r"""Test serialization of dict result."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            data = {"key": "value", "number": 42}
            result = toolkit._serialize_result(data)

            parsed = json.loads(result)
            assert parsed == data

    def test_serialize_result_list(self):
        r"""Test serialization of list result."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            data = [1, 2, 3, "test"]
            result = toolkit._serialize_result(data)

            parsed = json.loads(result)
            assert parsed == data

    def test_store_original_content(self):
        r"""Test storing original content to file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            offload_id = "test-store"
            content = "Test content to store"
            meta = OffloadedOutput(
                offload_id=offload_id,
                tool_name="test_tool",
                tool_call_id="call-1",
                record_uuid="uuid-1",
                original_length=len(content),
                summary="Test summary",
                file_path=str(toolkit.outputs_dir / f"{offload_id}.txt"),
                timestamp=1000,
                offloaded_at="2024-01-01T00:00:00",
            )

            path = toolkit._store_original_content(content, offload_id, meta)

            # Verify content file
            content_file = Path(path)
            assert content_file.exists()
            assert content_file.read_text() == content

            # Verify metadata file
            meta_file = toolkit.outputs_dir / f"{offload_id}.meta.json"
            assert meta_file.exists()

            # Verify index
            assert offload_id in toolkit._offloaded_outputs

    def test_index_persistence(self):
        r"""Test that index is saved to file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            offload_id = "persist-test"
            meta = OffloadedOutput(
                offload_id=offload_id,
                tool_name="test_tool",
                tool_call_id="call-1",
                record_uuid="uuid-1",
                original_length=100,
                summary="Test",
                file_path="/path",
                timestamp=1000,
                offloaded_at="2024-01-01T00:00:00",
            )

            toolkit._offloaded_outputs[offload_id] = meta
            toolkit._save_index()

            # Verify index file
            assert toolkit.index_file.exists()
            index_data = json.loads(toolkit.index_file.read_text())
            assert offload_id in index_data


class TestOffloadedOutput:
    r"""Test suite for OffloadedOutput dataclass."""

    def test_dataclass_fields(self):
        r"""Test OffloadedOutput has all required fields."""
        output = OffloadedOutput(
            offload_id="test-id",
            tool_name="test_tool",
            tool_call_id="call-123",
            record_uuid="uuid-456",
            original_length=1000,
            summary="Test summary",
            file_path="/path/to/file.txt",
            timestamp=1234567890.0,
            offloaded_at="2024-01-01T00:00:00",
        )

        assert output.offload_id == "test-id"
        assert output.tool_name == "test_tool"
        assert output.tool_call_id == "call-123"
        assert output.record_uuid == "uuid-456"
        assert output.original_length == 1000
        assert output.summary == "Test summary"
        assert output.file_path == "/path/to/file.txt"
        assert output.timestamp == 1234567890.0
        assert output.offloaded_at == "2024-01-01T00:00:00"
