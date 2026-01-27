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

    def test_init_with_default_threshold(self):
        r"""Test default auto_offload_threshold value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            assert toolkit.auto_offload_threshold == 5000

    def test_init_with_custom_threshold(self):
        r"""Test custom auto_offload_threshold value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                auto_offload_threshold=3000,
            )
            assert toolkit.auto_offload_threshold == 3000

    def test_init_with_default_summary_length(self):
        r"""Test default max_summary_length value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)
            assert toolkit.max_summary_length == 500

    def test_init_with_custom_summary_length(self):
        r"""Test custom max_summary_length value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                max_summary_length=200,
            )
            assert toolkit.max_summary_length == 200

    def test_generate_summary_short_content(self):
        r"""Test that short content is not truncated."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                max_summary_length=100,
            )

            content = "Short content"
            summary = toolkit._generate_summary(content)

            assert summary == content

    def test_generate_summary_long_content(self):
        r"""Test that long content is truncated with ellipsis."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                max_summary_length=20,
            )

            content = "This is a very long content that should be truncated"
            summary = toolkit._generate_summary(content)

            assert len(summary) == 20
            assert summary.endswith("...")
            assert summary == "This is a very lo..."

    def test_process_tool_output_below_threshold(self):
        r"""Test that output below threshold is not offloaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                auto_offload_threshold=100,
            )

            output = "Short output"
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result["offloaded"] is False
            assert result["output"] == output
            assert result["original_length"] == len(output)
            assert "offload_id" not in result

    def test_process_tool_output_above_threshold(self):
        r"""Test that output above threshold is offloaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                auto_offload_threshold=50,
                max_summary_length=30,
            )

            output = "x" * 100  # 100 chars, above 50 threshold
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result["offloaded"] is True
            assert "offload_id" in result
            assert result["original_length"] == 100
            assert "[OFFLOADED OUTPUT" in result["output"]
            assert result["offload_id"] in result["output"]

            # Verify file was created
            offload_id = result["offload_id"]
            content_file = toolkit.outputs_dir / f"{offload_id}.txt"
            assert content_file.exists()
            assert content_file.read_text() == output

    def test_process_tool_output_disabled(self):
        r"""Test that auto-offload can be disabled with threshold=0."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                auto_offload_threshold=0,  # Disabled
            )

            output = "x" * 10000  # Very long output
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result["offloaded"] is False
            assert result["output"] == output

    def test_process_tool_output_with_dict(self):
        r"""Test that dict output is serialized to JSON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                auto_offload_threshold=10,
            )

            output = {"key": "value", "nested": {"a": 1, "b": 2}}
            result = toolkit.process_tool_output(
                tool_name="test_tool",
                tool_call_id="call-1",
                output=output,
            )

            assert result["offloaded"] is True
            # Verify JSON serialization
            offload_id = result["offload_id"]
            content_file = toolkit.outputs_dir / f"{offload_id}.txt"
            content = content_file.read_text()
            assert '"key": "value"' in content

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

    def test_list_offloaded_tool_outputs_empty(self):
        r"""Test listing when no outputs have been offloaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            result = toolkit.list_offloaded_tool_outputs()

            assert isinstance(result, list)
            assert len(result) == 0

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

            assert isinstance(result, list)
            assert len(result) == 1

            item = result[0]
            assert item["offload_id"] == "id-1"
            assert item["tool_name"] == "tool_a"
            assert item["original_length"] == 5000
            assert item["summary"] == "Summary of tool A output"
            assert item["file_path"] == "/path/to/file"
            assert item["offloaded_at"] == "2024-01-01T00:00:00"

    def test_get_tools_returns_only_retrieval_tools(self):
        r"""Test that get_tools only returns retrieve and list tools."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(working_directory=tmp_dir)

            tools = toolkit.get_tools()

            assert len(tools) == 2
            tool_names = [t.get_function_name() for t in tools]
            assert "retrieve_offloaded_tool_output" in tool_names
            assert "list_offloaded_tool_outputs" in tool_names

    def test_end_to_end_offload_and_retrieve(self):
        r"""Test complete flow: offload via process_tool_output, then retrieve."""  # noqa: E501
        with tempfile.TemporaryDirectory() as tmp_dir:
            toolkit = ToolOutputOffloadToolkit(
                working_directory=tmp_dir,
                auto_offload_threshold=50,
                max_summary_length=30,
            )

            # Step 1: Process a large output (triggers auto-offload)
            original_output = "A" * 200
            process_result = toolkit.process_tool_output(
                tool_name="search",
                tool_call_id="call-123",
                output=original_output,
            )

            assert process_result["offloaded"] is True
            offload_id = process_result["offload_id"]

            # Step 2: List offloaded outputs
            list_result = toolkit.list_offloaded_tool_outputs()
            assert len(list_result) == 1
            assert list_result[0]["offload_id"] == offload_id
            assert list_result[0]["tool_name"] == "search"

            # Step 3: Retrieve the original content
            retrieve_result = toolkit.retrieve_offloaded_tool_output(
                offload_id
            )
            assert retrieve_result["content"] == original_output
            assert retrieve_result["original_length"] == 200


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
