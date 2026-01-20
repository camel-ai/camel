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

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

from camel.memories.records import MemoryRecord
from camel.messages import FunctionCallingMessage
from camel.toolkits.tool_output_offload_toolkit import (
    OffloadedOutput,
    ToolOutputOffloadToolkit,
)
from camel.types import OpenAIBackendRole, RoleType


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

    def test_list_offloadable_tool_outputs_no_agent(self):
        r"""Test listing with no registered agent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.list_offloadable_tool_outputs()

            assert "No tool outputs found" in result
            assert "Total tool outputs in memory: 0" in result

    def test_list_offloadable_tool_outputs_empty_memory(self):
        r"""Test listing with empty memory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Mock agent with empty memory
            mock_agent = MagicMock()
            mock_memory = MagicMock()
            mock_memory.get_records.return_value = []

            mock_agent.memory = mock_memory
            toolkit._agent = mock_agent

            result = toolkit.list_offloadable_tool_outputs()

            assert "No tool outputs found" in result

    def test_list_offloadable_tool_outputs_filters_by_length(self):
        r"""Test that outputs below min_length are excluded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                min_output_length=100,
            )

            # Mock agent with tool outputs of varying lengths
            mock_agent = MagicMock()
            mock_memory = MagicMock()
            mock_memory.get_records.return_value = [
                MemoryRecord(
                    message=FunctionCallingMessage(
                        role_name="assistant",
                        role_type=RoleType.ASSISTANT,
                        meta_dict=None,
                        content="",
                        func_name="short_tool",
                        tool_call_id="call-1",
                        result="short",
                    ),
                    role_at_backend=OpenAIBackendRole.FUNCTION,
                ),
                MemoryRecord(
                    message=FunctionCallingMessage(
                        role_name="assistant",
                        role_type=RoleType.ASSISTANT,
                        meta_dict=None,
                        content="",
                        func_name="long_tool",
                        tool_call_id="call-2",
                        result="x" * 200,
                    ),
                    role_at_backend=OpenAIBackendRole.FUNCTION,
                ),
            ]

            mock_agent.memory = mock_memory
            toolkit._agent = mock_agent

            result = toolkit.list_offloadable_tool_outputs()

            assert "long_tool" in result
            assert "short_tool" not in result
            assert "1 offloadable" in result

    def test_offload_tool_output_with_summary_no_cached_list(self):
        r"""Test error when no cached list exists."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.offload_tool_output_with_summary(0, "summary")

            assert "No offloadable outputs cached" in result
            assert "list_offloadable_tool_outputs()" in result

    def test_offload_tool_output_with_summary_invalid_index(self):
        r"""Test error handling for invalid index."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            toolkit._last_offloadable_list = [{"test": "data"}]

            result = toolkit.offload_tool_output_with_summary(5, "summary")

            assert "Invalid index" in result

    def test_offload_tool_output_with_summary_empty_summary(self):
        r"""Test error when summary is empty."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            toolkit._last_offloadable_list = [
                {
                    "index": 0,
                    "uuid": "uuid-1",
                    "tool_name": "test_tool",
                    "tool_call_id": "call-1",
                    "result": "x" * 10,
                    "result_str": "x" * 10,
                    "timestamp": 1000,
                    "length": 10,
                }
            ]

            result = toolkit.offload_tool_output_with_summary(0, "")

            assert "Summary is required" in result

    def test_offload_tool_output_with_summary_success(self):
        r"""Test successful offload flow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            record_uuid = "123e4567-e89b-12d3-a456-426614174000"
            memory_record = MemoryRecord(
                message=FunctionCallingMessage(
                    role_name="assistant",
                    role_type=RoleType.ASSISTANT,
                    meta_dict=None,
                    content="",
                    func_name="test_tool",
                    tool_call_id="call-1",
                    result="x" * 20,
                ),
                role_at_backend=OpenAIBackendRole.FUNCTION,
                uuid=UUID(record_uuid),
            )

            mock_memory = MagicMock()
            mock_memory.get_records.return_value = [memory_record]
            mock_memory.replace_record_by_uuid.return_value = None

            mock_agent = MagicMock()
            mock_agent.memory = mock_memory
            toolkit._agent = mock_agent

            toolkit._last_offloadable_list = [
                {
                    "index": 0,
                    "uuid": record_uuid,
                    "tool_name": "test_tool",
                    "tool_call_id": "call-1",
                    "result": "x" * 20,
                    "result_str": "x" * 20,
                    "timestamp": 1000,
                    "length": 20,
                }
            ]

            result = toolkit.offload_tool_output_with_summary(
                0, "short summary"
            )

            assert "Successfully offloaded output" in result
            assert "Offload ID:" in result
            mock_memory.replace_record_by_uuid.assert_called_once()

            offload_id = ""
            for line in result.splitlines():
                if line.startswith("Offload ID:"):
                    offload_id = line.split("Offload ID:", 1)[1].strip()
                    break

            assert offload_id
            content_file = toolkit.outputs_dir / f"{offload_id}.txt"
            assert content_file.exists()

    def test_retrieve_offloaded_tool_output_not_found(self):
        r"""Test error handling for missing offload_id."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.retrieve_offloaded_tool_output("nonexistent-id")

            assert "not found" in result
            assert "list_offloaded_tool_outputs()" in result

    def test_retrieve_offloaded_tool_output_success(self):
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

            result = toolkit.retrieve_offloaded_tool_output(offload_id)

            assert original_content in result
            assert "Retrieved Original Content" in result

    def test_list_offloaded_tool_outputs_empty(self):
        r"""Test listing when no outputs have been offloaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.list_offloaded_tool_outputs()

            assert "No outputs have been offloaded" in result

    def test_list_offloaded_tool_outputs_with_data(self):
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

            result = toolkit.list_offloaded_tool_outputs()

            assert "id-1" in result
            assert "tool_a" in result
            assert "5000" in result
            assert "1 total" in result


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
