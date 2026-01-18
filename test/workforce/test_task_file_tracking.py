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

"""Unit tests for file information tracking in task summaries."""

from unittest.mock import MagicMock

import pytest

from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.agents import ChatAgent


class TestTaskFileTracking:
    r"""Test file information tracking in task summaries."""

    def test_extract_file_paths_from_write_operation(self):
        r"""Test extracting file paths from write_to_file tool calls."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        # Mock tool call with write_to_file
        mock_call = MagicMock()
        mock_call.tool_name = 'write_to_file'
        mock_call.args = {'filename': 'README.md', 'content': '...'}
        mock_call.result = (
            "Content successfully written to file: /full/path/to/README.md"
        )

        file_paths = worker._extract_file_paths([mock_call])

        assert file_paths == ["/full/path/to/README.md"]

    def test_extract_multiple_file_paths(self):
        r"""Test extracting multiple file paths."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        # Mock multiple write_to_file calls
        mock_call1 = MagicMock()
        mock_call1.tool_name = 'write_to_file'
        mock_call1.args = {'filename': 'README.md'}
        mock_call1.result = (
            "Content successfully written to file: /path/to/README.md"
        )

        mock_call2 = MagicMock()
        mock_call2.tool_name = 'write_to_file'
        mock_call2.args = {'filename': 'setup.py'}
        mock_call2.result = (
            "Content successfully written to file: /path/to/setup.py"
        )

        file_paths = worker._extract_file_paths([mock_call1, mock_call2])

        assert len(file_paths) == 2
        assert "/path/to/README.md" in file_paths
        assert "/path/to/setup.py" in file_paths

    def test_no_file_paths_returns_none(self):
        r"""Test that tasks without file operations return None."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        # Mock call without write_to_file
        mock_call = MagicMock()
        mock_call.tool_name = 'search_web'
        mock_call.args = {'query': 'test'}

        file_paths = worker._extract_file_paths([mock_call])

        assert file_paths is None

    def test_extract_file_paths_none_input(self):
        r"""Test extracting file paths with None input."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        file_paths = worker._extract_file_paths(None)

        assert file_paths is None

    def test_extract_file_paths_empty_list(self):
        r"""Test extracting file paths with empty list."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        file_paths = worker._extract_file_paths([])

        assert file_paths is None

    @pytest.mark.asyncio
    async def test_generate_file_description_create(self):
        r"""Test file description generation for create action."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        description = await worker._generate_file_description(
            "Create a Python Flask server",
            ["/path/to/server.py"]
        )

        assert "creates" in description.lower()
        assert "server.py" in description

    @pytest.mark.asyncio
    async def test_generate_file_description_multiple_files(self):
        r"""Test file description generation for multiple files."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        description = await worker._generate_file_description(
            "Create README.md and setup.py",
            ["/path/to/README.md", "/path/to/setup.py"]
        )

        assert "creates" in description.lower()
        assert "README.md" in description
        assert "setup.py" in description

    @pytest.mark.asyncio
    async def test_generate_file_description_update_action(self):
        r"""Test file description generation for update action."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        description = await worker._generate_file_description(
            "Update the configuration file",
            ["/path/to/config.json"]
        )

        assert "updates" in description.lower()

    @pytest.mark.asyncio
    async def test_generate_file_description_no_extension(self):
        r"""Test file description generation for files without extension."""
        worker = SingleAgentWorker(
            worker=ChatAgent(),
            description="Test worker"
        )

        description = await worker._generate_file_description(
            "Create a Makefile",
            ["/path/to/Makefile"]
        )

        assert "creates" in description.lower()
        assert "files:" in description.lower()
