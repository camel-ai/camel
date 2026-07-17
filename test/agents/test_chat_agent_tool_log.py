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
"""Tests for optionally saving full tool outputs before truncation."""

import inspect
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from camel.agents import ChatAgent
from camel.models import StubModel
from camel.types import ModelType


class _CharTokenCounter:
    def encode(self, text):
        return [ord(char) for char in text]

    def decode(self, token_ids):
        return "".join(chr(token_id) for token_id in token_ids)


def test_tool_log_dir_is_appended_to_constructor():
    parameters = list(inspect.signature(ChatAgent.__init__).parameters)
    assert parameters.index("tool_log_dir") > parameters.index(
        "summary_window_ratio"
    )


def test_tool_log_dir_is_opt_in_and_preserved_by_clone(tmp_path):
    default_agent = ChatAgent(model=StubModel(ModelType.STUB))
    assert default_agent._tool_log_dir is None
    assert default_agent.clone()._tool_log_dir is None

    log_dir = tmp_path / "relative" / ".." / "logs"
    configured_agent = ChatAgent(
        model=StubModel(ModelType.STUB),
        tool_log_dir=log_dir,
    )
    assert configured_agent._tool_log_dir == log_dir.resolve()
    assert configured_agent.clone()._tool_log_dir == log_dir.resolve()


@pytest.fixture
def agent(tmp_path):
    """A ChatAgent with just enough state for these methods."""
    a = ChatAgent.__new__(ChatAgent)
    a._tool_log_dir = tmp_path / "camel_tool_logs"
    a._token_limit = 4096
    a.summarize_threshold = None
    a.model_backend = MagicMock()
    a.model_backend.token_counter = _CharTokenCounter()
    return a


class TestSaveToolOutputLog:
    def test_creates_log_file(self, agent):
        path = agent._save_tool_output_log("my_tool", "full content")
        assert path is not None
        assert Path(path).exists()
        assert Path(path).is_absolute()

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
        # dir doesn't exist yet - method should mkdir(parents=True) for us
        agent._tool_log_dir = tmp_path / "new" / "nested" / "dir"
        assert not agent._tool_log_dir.exists()
        agent._save_tool_output_log("tool", "content")
        assert agent._tool_log_dir.exists()

    def test_returns_none_on_write_failure(self, agent, tmp_path):
        # Point _tool_log_dir at an existing *file* so mkdir() raises
        # FileExistsError / NotADirectoryError under the hood. We just
        # want to confirm this fails quietly (returns None) rather than
        # blowing up the whole tool-call flow.
        bad_path = tmp_path / "i_am_a_file"
        bad_path.write_text("block")
        agent._tool_log_dir = bad_path
        result = agent._save_tool_output_log("tool", "content")
        assert result is None

    def test_handles_non_ascii_content(self, agent):
        # Tool output can easily contain non-ASCII text (e.g. a web
        # search result in another language) - make sure we're writing
        # with utf-8 and not silently mangling it.
        content = "café, 日本語, emoji 🚀"
        path = agent._save_tool_output_log("my_tool", content)
        assert Path(path).read_text(encoding="utf-8") == content

    @pytest.mark.parametrize(
        "func_name",
        ["../escaped", "/tmp/escaped", r"..\escaped"],
    )
    def test_sanitizes_func_name(self, agent, func_name):
        path = agent._save_tool_output_log(func_name, "content")
        assert Path(path).parent == agent._tool_log_dir

    def test_handles_func_name_without_safe_characters(self, agent):
        path = agent._save_tool_output_log("../", "content")
        assert Path(path).name.startswith("tool_")

    def test_uses_private_file_permissions(self, agent):
        path = agent._save_tool_output_log("my_tool", "content")
        if os.name != "nt":
            assert stat.S_IMODE(Path(path).stat().st_mode) & 0o077 == 0
            assert (
                stat.S_IMODE(agent._tool_log_dir.stat().st_mode) & 0o077 == 0
            )

    def test_does_not_save_without_configured_directory(self, agent):
        agent._tool_log_dir = None
        assert agent._save_tool_output_log("my_tool", "content") is None


class TestTruncateToolResult:
    def test_short_result_not_truncated(self, agent):
        result, was_truncated = agent._truncate_tool_result("tool", "short")
        assert was_truncated is False
        assert result == "short"

    def test_long_result_is_truncated(self, agent):
        result, was_truncated = agent._truncate_tool_result(
            "tool", "x" * 50000
        )
        assert was_truncated is True
        assert len(result) < 50000

    def test_truncation_creates_log_file(self, agent):
        agent._truncate_tool_result("my_tool", "x" * 50000)
        log_files = list(agent._tool_log_dir.glob("my_tool_*.log"))
        assert len(log_files) == 1

    def test_truncation_notice_contains_log_path(self, agent):
        result, _ = agent._truncate_tool_result("my_tool", "x" * 50000)
        assert "Full output saved to:" in result

    def test_log_file_contains_full_original_output(self, agent):
        long_output = "x" * 50000
        agent._truncate_tool_result("my_tool", long_output)
        log_file = next(agent._tool_log_dir.glob("my_tool_*.log"))
        assert log_file.read_text(encoding="utf-8") == long_output

    def test_no_log_file_when_not_truncated(self, agent):
        agent._truncate_tool_result("my_tool", "short")
        # nothing should have been written at all, dir shouldn't exist
        assert not agent._tool_log_dir.exists()

    def test_no_log_notice_when_logging_is_disabled(self, agent):
        agent._tool_log_dir = None
        result, _ = agent._truncate_tool_result("my_tool", "x" * 50000)
        assert "Full output saved to:" not in result
        assert "log saving failed" not in result

    def test_truncated_result_respects_token_limit(self, agent):
        agent._token_limit = 1000
        result, _ = agent._truncate_tool_result("my_tool", "x" * 50000)
        assert agent._get_token_count(result) <= 900

    def test_two_truncated_calls_produce_two_log_files(self, agent):
        # Regression check: filenames need to be unique per call (e.g.
        # timestamped or uuid-suffixed), otherwise the second truncation
        # would silently clobber the first log.
        agent._truncate_tool_result("my_tool", "a" * 50000)
        agent._truncate_tool_result("my_tool", "b" * 50000)
        log_files = list(agent._tool_log_dir.glob("my_tool_*.log"))
        assert len(log_files) == 2

    def test_concurrent_calls_produce_unique_log_files(self, agent):
        with ThreadPoolExecutor(max_workers=4) as executor:
            paths = list(
                executor.map(
                    lambda content: agent._save_tool_output_log(
                        "my_tool", content
                    ),
                    [str(index) for index in range(10)],
                )
            )
        assert len(paths) == len(set(paths))
