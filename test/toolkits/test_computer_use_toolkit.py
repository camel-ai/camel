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
"""Tests for the ComputerUseToolkit."""

from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import ComputerUseToolkit, FunctionTool


class TestComputerUseToolkit:
    """Tests for ComputerUseToolkit in local (non-Docker) mode."""

    @pytest.fixture
    def toolkit(self):
        """Create a toolkit instance in local mode (no Docker needed)."""
        return ComputerUseToolkit(
            display_width=1024,
            display_height=768,
            use_docker=False,
        )

    def test_init_local_mode(self, toolkit):
        """Toolkit initializes in local mode without Docker."""
        assert toolkit.display_width == 1024
        assert toolkit.display_height == 768
        assert toolkit.use_docker is False

    def test_get_tools_returns_function_tools(self, toolkit):
        """get_tools() returns a list of FunctionTool instances."""
        tools = toolkit.get_tools()
        assert len(tools) == 13
        assert all(isinstance(t, FunctionTool) for t in tools)

    def test_mouse_move_clamps_coordinates(self, toolkit):
        """Mouse coordinates are clamped to display bounds."""
        result = toolkit.mouse_move(2000, 2000)
        assert "1023" in result  # Clamped to width-1
        assert "767" in result   # Clamped to height-1

    def test_mouse_move_within_bounds(self, toolkit):
        """Mouse coordinates within bounds are used directly."""
        result = toolkit.mouse_move(500, 300)
        assert "(500, 300)" in result

    def test_get_screen_size(self, toolkit):
        """get_screen_size returns correct dimensions."""
        size = toolkit.get_screen_size()
        assert size == {"width": 1024, "height": 768}

    def test_get_cursor_position_default(self, toolkit):
        """Cursor starts at (0, 0)."""
        pos = toolkit.get_cursor_position()
        assert pos == {"x": 0, "y": 0}

    def test_get_cursor_position_after_move(self, toolkit):
        """Cursor position updates after mouse_move."""
        toolkit.mouse_move(100, 200)
        pos = toolkit.get_cursor_position()
        assert pos == {"x": 100, "y": 200}

    def test_scroll_up_positive(self, toolkit):
        """Positive scroll amount scrolls up."""
        with patch("subprocess.run"):
            result = toolkit.scroll(5)
            assert "up" in result

    def test_scroll_down_negative(self, toolkit):
        """Negative scroll amount scrolls down."""
        with patch("subprocess.run"):
            result = toolkit.scroll(-3)
            assert "down" in result

    def test_wait_capped_at_10(self, toolkit):
        """wait() caps at 10 seconds."""
        result = toolkit.wait(15.0)
        assert "10" in result  # Capped

    def test_key_combination(self, toolkit):
        """key_combination builds correct xdotool command."""
        with patch("subprocess.run") as mock_run:
            toolkit.key_combination(["ctrl", "c"])
            assert "ctrl+c" in str(mock_run.call_args)

    def test_type_text(self, toolkit):
        """type_text formats correctly."""
        with patch("subprocess.run"):
            result = toolkit.type_text("Hello, World!")
            assert "Typed: Hello, World!" in result

    def test_type_text_long_truncates_preview(self, toolkit):
        """Long text preview is truncated."""
        with patch("subprocess.run"):
            long_text = "A" * 100
            result = toolkit.type_text(long_text)
            assert "...]]" in result or "..." in result
            assert len(result) < 200
