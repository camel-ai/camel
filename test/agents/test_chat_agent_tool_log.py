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
"""Tests for tool output log saving on truncation (issue #3616)."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from camel.agents import ChatAgent


@pytest.fixture
def agent(tmp_path):
    """Minimal ChatAgent built with __new__ — no API key needed."""
    a = ChatAgent.__new__(ChatAgent)
    a._tool_log_dir = tmp_path / "camel_tool_logs"
    a._token_limit = 4096
    a.summarize_threshold = None
    # Mock token counter so we control how many tokens any string reports
    a.model_backend = MagicMock()
    return a


def _force_truncation(agent, token_count=5000):
    """Make the token counter return a high count to trigger truncation."""
    agent.model_backend.token_counter.encode.return_value = list(
        range(token_count)
    )


def _force_no_truncation(agent, token_count=10):
    """Make the token counter return a low count to skip truncation."""
    agent.model_backend.token_counter.encode.return_value = list(
        range(token_count)
    )


class TestSaveToolOutputLog:
    def test_creates_log_file(self, agent):
        path = agent._save_tool_output_log("my_tool", "full content")
        assert path is not None
        assert Path(path).exists()

    def test_log_file_contains_full_content(self, agent):
        content = "full output data"
        path = agent._save_tool_output_log("my_tool", content)
        assert Path(path).read_text(encoding="utf-8") == content

    def test_log_file_placed_in_tool_log_dir(self, agent):
        path = agent._save_tool_output_log("my_tool", "data")
        assert Path(path).parent == agent._tool_log_dir

    def test_log_filename_contains_func_name(self, agent):
        path = agent._save_tool_output_log("search_web", "data")
        assert "search_web" in Path(path).name

    def test_log_dir_created_automatically(self, agent, tmp_path):
        agent._tool_log_dir = tmp_path / "new" / "nested" / "dir"
        assert not agent._tool_log_dir.exists()
        agent._save_tool_output_log("tool", "content")
        assert agent._tool_log_dir.exists()

    def test_returns_none_on_write_failure(self, agent, tmp_path):
        # Point _tool_log_dir at an existing file so mkdir raises
        bad_path = tmp_path / "i_am_a_file"
        bad_path.write_text("block")
        agent._tool_log_dir = bad_path
        result = agent._save_tool_output_log("tool", "content")
        assert result is None


class TestTruncateToolResult:
    def test_short_result_not_truncated(self, agent):
        _force_no_truncation(agent)
        result, was_truncated = agent._truncate_tool_result("tool", "short")
        assert was_truncated is False
        assert result == "short"

    def test_long_result_is_truncated(self, agent):
        _force_truncation(agent)
        result, was_truncated = agent._truncate_tool_result(
            "tool", "x" * 50000
        )
        assert was_truncated is True
        assert len(result) < 50000

    def test_truncation_creates_log_file(self, agent):
        _force_truncation(agent)
        agent._truncate_tool_result("my_tool", "x" * 50000)
        log_files = list(agent._tool_log_dir.glob("my_tool_*.log"))
        assert len(log_files) == 1

    def test_truncation_notice_contains_log_path(self, agent):
        _force_truncation(agent)
        result, _ = agent._truncate_tool_result("my_tool", "x" * 50000)
        assert "Full output saved to:" in result

    def test_log_file_contains_full_original_output(self, agent):
        _force_truncation(agent)
        long_output = "x" * 50000
        agent._truncate_tool_result("my_tool", long_output)
        log_file = list(agent._tool_log_dir.glob("my_tool_*.log"))[0]
        assert log_file.read_text(encoding="utf-8") == long_output

    def test_no_log_file_when_not_truncated(self, agent):
        _force_no_truncation(agent)
        agent._truncate_tool_result("my_tool", "short")
        assert not agent._tool_log_dir.exists()