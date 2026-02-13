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
from unittest.mock import MagicMock, PropertyMock

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

    def test_init_default_hint_threshold(self):
        r"""Test default hint_threshold value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            assert toolkit.hint_threshold == 5000

    def test_init_custom_hint_threshold(self):
        r"""Test custom hint_threshold value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                hint_threshold=3000,
            )
            assert toolkit.hint_threshold == 3000

    def test_process_tool_output_none(self):
        r"""Test that None output returns None."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=None,
            )

            assert result is None

    def test_process_tool_output_below_threshold(self):
        r"""Test that output below threshold returns without hint."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                hint_threshold=100,
            )

            output = "Short output"
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result is not None
            assert result["output"] == output
            assert "hint_message" not in result

    def test_process_tool_output_above_threshold(self):
        r"""Test that output above threshold returns with hint."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                hint_threshold=50,
            )

            output = "x" * 100  # 100 chars, above 50 threshold
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result is not None
            assert result["output"] == output
            assert "hint_message" in result
            assert "OFFLOAD REQUIRED" in result["hint_message"]
            assert "test_tool" in result["hint_message"]
            assert "call-1" in result["hint_message"]
            assert "summarize_and_offload" in result["hint_message"]

    def test_process_tool_output_with_dict(self):
        r"""Test that dict output is handled correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                hint_threshold=10,
            )

            output = {"key": "value", "nested": {"a": 1}}
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result is not None
            assert result["output"] == output
            # Dict serializes to JSON which exceeds 10 char threshold
            assert "hint_message" in result

    def test_retrieve_offloaded_tool_output_not_found(self):
        r"""Test error handling for missing offload_id."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.retrieve_offloaded_tool_output("nonexistent-id")

            assert isinstance(result, dict)
            assert result["offload_id"] == "nonexistent-id"
            assert "error" in result
            assert "not found" in result["error"]

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

            assert isinstance(result, dict)
            assert result["offload_id"] == offload_id
            assert result["tool_name"] == "test_tool"
            assert result["content"] == original_content
            assert result["original_length"] == len(original_content)
            assert result["summary"] == "Test summary"
            assert result["file_path"] == str(content_file)
            assert result["offloaded_at"] == "2024-01-01T00:00:00"
            assert "error" not in result

    def test_get_tools_returns_correct_tools(self):
        r"""Test that get_tools returns the expected tools."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            tools = toolkit.get_tools()

            assert len(tools) == 2
            tool_names = [t.get_function_name() for t in tools]
            assert "summarize_and_offload" in tool_names
            assert "retrieve_offloaded_tool_output" in tool_names

    def test_summarize_and_offload_no_agent(self):
        r"""Test summarize_and_offload fails gracefully without agent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.summarize_and_offload(
                tool_call_id="call-1",
                summary="My summary",
            )

            assert result["success"] is False
            assert "No agent registered" in result["error"]

    def test_summarize_and_offload_tool_not_found(self):
        r"""Test summarize_and_offload with non-existent tool_call_id."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Create a mock agent with empty memory
            mock_agent = MagicMock()
            mock_memory = MagicMock()
            mock_memory.get_records.return_value = []
            type(mock_agent).memory = PropertyMock(return_value=mock_memory)
            toolkit._agent = mock_agent

            result = toolkit.summarize_and_offload(
                tool_call_id="nonexistent-call",
                summary="My summary",
            )

            assert result["success"] is False
            assert "not found in memory" in result["error"]

    def test_summarize_and_offload_success(self):
        r"""Test successful summarize_and_offload flow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Create mock message that looks like FunctionCallingMessage
            mock_message = MagicMock()
            mock_message.__class__.__name__ = "FunctionCallingMessage"
            mock_message.func_name = "browse_url"
            mock_message.tool_call_id = "call-123"
            mock_message.result = "A" * 10000  # Large content

            # Create mock record
            mock_record = MagicMock()
            mock_record.uuid = "record-uuid-456"
            mock_record.message = mock_message
            mock_record.timestamp = 1234567890.0

            # Setup model_copy to return a new mock with editable result
            new_mock_message = MagicMock()
            new_mock_message.result = mock_message.result
            new_mock_record = MagicMock()
            new_mock_record.message = new_mock_message
            mock_record.model_copy.return_value = new_mock_record

            # Create mock memory
            mock_memory = MagicMock()
            mock_memory.get_records.return_value = [mock_record]

            # Create mock agent
            mock_agent = MagicMock()
            type(mock_agent).memory = PropertyMock(return_value=mock_memory)
            toolkit._agent = mock_agent

            # Call summarize_and_offload
            result = toolkit.summarize_and_offload(
                tool_call_id="call-123",
                summary="This is a summary of a large web page about AI.",
            )

            # Verify success
            assert result["success"] is True
            assert "offload_id" in result
            assert result["tool_name"] == "browse_url"
            assert result["original_length"] == 10000
            assert result["summary_length"] > 0

            # Verify file was created
            offload_id = result["offload_id"]
            content_file = toolkit.outputs_dir / f"{offload_id}.txt"
            assert content_file.exists()
            assert content_file.read_text() == "A" * 10000

            # Verify metadata file was created
            meta_file = toolkit.outputs_dir / f"{offload_id}.meta.json"
            assert meta_file.exists()

            # Verify replace_record_by_uuid was called
            mock_memory.replace_record_by_uuid.assert_called_once()

    def test_summarize_and_offload_already_offloaded(self):
        r"""Test that re-offloading same tool_call_id fails."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            # Add an existing offloaded output
            toolkit._offloaded_outputs["existing-id"] = OffloadedOutput(
                offload_id="existing-id",
                tool_name="browse_url",
                tool_call_id="call-123",
                record_uuid="uuid-1",
                original_length=5000,
                summary="Existing summary",
                file_path="/path/to/file",
                timestamp=1000,
                offloaded_at="2024-01-01T00:00:00",
            )

            # Create mock message that matches the tool_call_id
            mock_message = MagicMock()
            mock_message.__class__.__name__ = "FunctionCallingMessage"
            mock_message.func_name = "browse_url"
            mock_message.tool_call_id = "call-123"
            mock_message.result = "Some content"

            mock_record = MagicMock()
            mock_record.uuid = "uuid-1"
            mock_record.message = mock_message
            mock_record.timestamp = 1000

            # Create mock agent with record in memory
            mock_agent = MagicMock()
            mock_memory = MagicMock()
            mock_memory.get_records.return_value = [mock_record]
            type(mock_agent).memory = PropertyMock(return_value=mock_memory)
            toolkit._agent = mock_agent

            result = toolkit.summarize_and_offload(
                tool_call_id="call-123",
                summary="New summary",
            )

            assert result["success"] is False
            assert "already been offloaded" in result["error"]


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
