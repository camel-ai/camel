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

import json
import tempfile
from pathlib import Path

import pytest

from camel.logging.llm_log_to_html import (
    format_message_content,
    generate_html,
    get_role_color,
    get_role_icon,
    parse_log_file,
    truncate_content,
)


@pytest.fixture
def sample_log_file():
    r"""Create a sample log file for testing.

    Returns:
        Path: Path to the temporary log file.
    """
    content = """
================================================================================
PROMPT #1 - gpt-4 (iteration 0)
Timestamp: 2024-01-15T10:30:00.123456
================================================================================
[
  {
    "role": "system",
    "content": "You are a helpful assistant."
  },
  {
    "role": "user",
    "content": "Hello!"
  }
]
================================================================================

================================================================================
PROMPT #2 - gpt-3.5-turbo (iteration 1)
Timestamp: 2024-01-15T10:31:00.123456
================================================================================
[
  {
    "role": "assistant",
    "content": "Hi! How can I help you?"
  },
  {
    "role": "user",
    "content": "Tell me about Python."
  }
]
================================================================================
"""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.log', delete=False, encoding='utf-8'
    ) as f:
        f.write(content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def sample_prompts():
    r"""Create sample parsed prompts for testing.

    Returns:
        list: Sample prompts data.
    """
    return [
        {
            'number': '1',
            'model': 'gpt-4',
            'iteration': '0',
            'timestamp': '2024-01-15T10:30:00',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Hello!'},
            ],
        },
        {
            'number': '2',
            'model': 'gpt-3.5-turbo',
            'iteration': '1',
            'timestamp': '2024-01-15T10:31:00',
            'messages': [
                {'role': 'assistant', 'content': 'Hi there!'},
            ],
        },
    ]


class TestParseLogFile:
    r"""Test suite for parse_log_file function."""

    def test_parse_valid_log_file(self, sample_log_file: Path) -> None:
        r"""Test parsing a valid log file."""
        prompts = parse_log_file(sample_log_file)

        assert len(prompts) == 2
        assert prompts[0]['number'] == '1'
        assert prompts[0]['model'] == 'gpt-4'
        assert prompts[0]['iteration'] == '0'
        assert len(prompts[0]['messages']) == 2

        assert prompts[1]['number'] == '2'
        assert prompts[1]['model'] == 'gpt-3.5-turbo'
        assert prompts[1]['iteration'] == '1'

    def test_parse_empty_log_file(self) -> None:
        r"""Test parsing an empty log file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.log', delete=False
        ) as f:
            temp_path = Path(f.name)

        try:
            prompts = parse_log_file(temp_path)
            assert prompts == []
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_malformed_json(self) -> None:
        r"""Test parsing log file with malformed JSON."""
        content = """
================================================================================
PROMPT #1 - gpt-4 (iteration 0)
Timestamp: 2024-01-15T10:30:00.123456
================================================================================
{invalid json content}
================================================================================
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.log', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            prompts = parse_log_file(temp_path)
            # Should skip malformed entries
            assert prompts == []
        finally:
            temp_path.unlink(missing_ok=True)


class TestTruncateContent:
    r"""Test suite for truncate_content function."""

    def test_truncate_long_content(self) -> None:
        r"""Test truncating content longer than max_length."""
        long_text = "a" * 1000
        result = truncate_content(long_text, max_length=100)

        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")
        assert result.startswith("a" * 100)

    def test_truncate_short_content(self) -> None:
        r"""Test that short content is not truncated."""
        short_text = "Hello, world!"
        result = truncate_content(short_text, max_length=100)

        assert result == short_text

    def test_truncate_exact_length(self) -> None:
        r"""Test content exactly at max_length."""
        text = "a" * 500
        result = truncate_content(text, max_length=500)

        assert result == text

    def test_truncate_custom_max_length(self) -> None:
        r"""Test truncation with custom max_length."""
        text = "a" * 1000
        result = truncate_content(text, max_length=50)

        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")


class TestFormatMessageContent:
    r"""Test suite for format_message_content function."""

    def test_format_string_content(self) -> None:
        r"""Test formatting simple string content."""
        content = "Hello, world!"
        result = format_message_content(content)

        assert result == "Hello, world!"

    def test_format_escapes_html(self) -> None:
        r"""Test that HTML characters are escaped."""
        content = "<script>alert('xss')</script>"
        result = format_message_content(content)

        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        assert "<script>" not in result

    def test_format_list_content(self) -> None:
        r"""Test formatting list content."""
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "image", "url": "http://example.com"},
        ]
        result = format_message_content(content)

        assert "type" in result
        assert "text" in result
        assert "Hello" in result

    def test_format_special_characters(self) -> None:
        r"""Test formatting with special characters."""
        content = "Test & < > \" '"
        result = format_message_content(content)

        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result


class TestGetRoleColor:
    r"""Test suite for get_role_color function."""

    def test_system_role_color(self) -> None:
        r"""Test color for system role."""
        color = get_role_color('system')
        assert color == 'rgba(0, 240, 255, 0.1)'

    def test_user_role_color(self) -> None:
        r"""Test color for user role."""
        color = get_role_color('user')
        assert color == 'rgba(255, 42, 109, 0.1)'

    def test_assistant_role_color(self) -> None:
        r"""Test color for assistant role."""
        color = get_role_color('assistant')
        assert color == 'rgba(255, 208, 10, 0.1)'

    def test_tool_role_color(self) -> None:
        r"""Test color for tool role."""
        color = get_role_color('tool')
        assert color == 'rgba(0, 240, 255, 0.15)'

    def test_unknown_role_color(self) -> None:
        r"""Test default color for unknown role."""
        color = get_role_color('unknown')
        assert color == 'rgba(255, 255, 255, 0.05)'


class TestGetRoleIcon:
    r"""Test suite for get_role_icon function."""

    def test_system_role_icon(self) -> None:
        r"""Test icon for system role."""
        icon = get_role_icon('system')
        assert icon == '⚙️'

    def test_user_role_icon(self) -> None:
        r"""Test icon for user role."""
        icon = get_role_icon('user')
        assert icon == '👤'

    def test_assistant_role_icon(self) -> None:
        r"""Test icon for assistant role."""
        icon = get_role_icon('assistant')
        assert icon == '🤖'

    def test_tool_role_icon(self) -> None:
        r"""Test icon for tool role."""
        icon = get_role_icon('tool')
        assert icon == '🔧'

    def test_unknown_role_icon(self) -> None:
        r"""Test default icon for unknown role."""
        icon = get_role_icon('unknown')
        assert icon == '📝'


class TestGenerateHtml:
    r"""Test suite for generate_html function."""

    def test_generate_html_basic(self, sample_prompts: list) -> None:
        r"""Test basic HTML generation."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            generate_html(sample_prompts, output_path)

            assert output_path.exists()

            # Read and verify HTML content
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            assert '<!DOCTYPE html>' in html_content
            assert '<html' in html_content
            assert 'LLM LOG VISUALIZATION' in html_content
            assert 'gpt-4' in html_content
            assert 'gpt-3.5-turbo' in html_content

        finally:
            output_path.unlink(missing_ok=True)

    def test_generate_html_includes_stats(
        self, sample_prompts: list
    ) -> None:
        r"""Test that HTML includes statistics."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            generate_html(sample_prompts, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Check for stats placeholders being filled
            assert '<div class="stat-value">2</div>' in html_content  # total_prompts
            assert 'Total Prompts' in html_content
            assert 'Total Messages' in html_content
            assert 'Max Iteration' in html_content

        finally:
            output_path.unlink(missing_ok=True)

    def test_generate_html_with_empty_prompts(self) -> None:
        r"""Test HTML generation with empty prompts list."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            generate_html([], output_path)

            assert output_path.exists()

            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            assert '<!DOCTYPE html>' in html_content
            assert '<div class="stat-value">0</div>' in html_content

        finally:
            output_path.unlink(missing_ok=True)

    def test_generate_html_handles_unicode(self) -> None:
        r"""Test that HTML generation handles Unicode correctly."""
        unicode_prompts = [
            {
                'number': '1',
                'model': 'gpt-4',
                'iteration': '0',
                'timestamp': '2024-01-15T10:30:00',
                'messages': [
                    {'role': 'user', 'content': 'Hello 你好 مرحبا 🌍'},
                    {'role': 'assistant', 'content': 'Hi there! 👋'},
                ],
            }
        ]

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False
        ) as f:
            output_path = Path(f.name)

        try:
            generate_html(unicode_prompts, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            assert '你好' in html_content
            assert 'مرحبا' in html_content
            assert '🌍' in html_content
            assert '👋' in html_content

        finally:
            output_path.unlink(missing_ok=True)

    def test_generate_html_template_exists(self) -> None:
        r"""Test that HTML template file exists and is loaded."""
        template_path = (
            Path(__file__).parent.parent.parent
            / 'camel'
            / 'logging'
            / 'templates'
            / 'log_viewer.html'
        )

        assert template_path.exists(), (
            f"HTML template not found at {template_path}"
        )

        # Verify template has required placeholders
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        assert '{total_prompts}' in template_content
        assert '{total_messages}' in template_content
        assert '{max_iteration}' in template_content
        assert '{prompts_html}' in template_content
