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

from camel.logging import PromptLogger


@pytest.fixture
def temp_log_file():
    r"""Create a temporary log file for testing.

    Returns:
        str: Path to the temporary log file.
    """
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.log', delete=False
    ) as f:
        yield f.name
    # Cleanup after test
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def sample_messages():
    r"""Create sample OpenAI messages for testing.

    Returns:
        list: Sample messages in OpenAI format.
    """
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi! How can I help you?"},
    ]


class TestPromptLogger:
    r"""Test suite for PromptLogger class."""

    def test_logger_initialization(self, temp_log_file: str) -> None:
        r"""Test that PromptLogger initializes correctly."""
        logger = PromptLogger(temp_log_file)

        assert logger.log_file_path == temp_log_file
        assert logger.prompt_counter == 0
        assert Path(temp_log_file).parent.exists()

    def test_logger_creates_parent_directory(self) -> None:
        r"""Test that logger creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(
                Path(tmpdir) / "nested" / "directories" / "test.log"
            )
            logger = PromptLogger(log_path)

            assert Path(log_path).parent.exists()
            assert logger.log_file_path == log_path

    def test_log_prompt_basic(
        self, temp_log_file: str, sample_messages: list
    ) -> None:
        r"""Test basic prompt logging functionality."""
        logger = PromptLogger(temp_log_file)

        counter = logger.log_prompt(
            sample_messages, model_info="gpt-4", iteration=1
        )

        assert counter == 1
        assert logger.prompt_counter == 1
        assert Path(temp_log_file).exists()

        # Verify file content
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "PROMPT #1" in content
            assert "gpt-4" in content
            assert "iteration 1" in content
            # Check that the JSON is present (with pretty printing)
            assert '"role": "system"' in content
            assert '"content": "You are a helpful assistant."' in content

    def test_log_multiple_prompts(
        self, temp_log_file: str, sample_messages: list
    ) -> None:
        r"""Test logging multiple prompts increments counter correctly."""
        logger = PromptLogger(temp_log_file)

        counter1 = logger.log_prompt(sample_messages, model_info="gpt-4")
        counter2 = logger.log_prompt(sample_messages, model_info="gpt-3.5")
        counter3 = logger.log_prompt(sample_messages, model_info="gpt-4")

        assert counter1 == 1
        assert counter2 == 2
        assert counter3 == 3
        assert logger.prompt_counter == 3

    def test_log_prompt_with_default_parameters(
        self, temp_log_file: str, sample_messages: list
    ) -> None:
        r"""Test logging with default model_info and iteration."""
        logger = PromptLogger(temp_log_file)

        counter = logger.log_prompt(sample_messages)

        assert counter == 1

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "PROMPT #1" in content
            assert "iteration 0" in content

    def test_log_prompt_preserves_unicode(
        self, temp_log_file: str
    ) -> None:
        r"""Test that unicode characters are preserved in logs."""
        logger = PromptLogger(temp_log_file)

        unicode_messages = [
            {"role": "user", "content": "Hello 你好 مرحبا 🌍"},
            {"role": "assistant", "content": "Hi there! 👋"},
        ]

        logger.log_prompt(unicode_messages)

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "你好" in content
            assert "مرحبا" in content
            assert "🌍" in content
            assert "👋" in content

    def test_log_prompt_with_empty_messages(
        self, temp_log_file: str
    ) -> None:
        r"""Test logging with empty message list."""
        logger = PromptLogger(temp_log_file)

        counter = logger.log_prompt([])

        assert counter == 1
        assert Path(temp_log_file).exists()

    def test_get_stats_initial(self, temp_log_file: str) -> None:
        r"""Test get_stats returns correct initial values."""
        logger = PromptLogger(temp_log_file)

        stats = logger.get_stats()

        assert stats['total_prompts'] == 0
        assert stats['log_file'] == temp_log_file
        assert isinstance(stats['file_exists'], bool)

    def test_get_stats_after_logging(
        self, temp_log_file: str, sample_messages: list
    ) -> None:
        r"""Test get_stats returns correct values after logging."""
        logger = PromptLogger(temp_log_file)

        logger.log_prompt(sample_messages)
        logger.log_prompt(sample_messages)

        stats = logger.get_stats()

        assert stats['total_prompts'] == 2
        assert stats['log_file'] == temp_log_file
        assert stats['file_exists'] is True

    def test_log_file_format(
        self, temp_log_file: str, sample_messages: list
    ) -> None:
        r"""Test that log file has correct format with separators."""
        logger = PromptLogger(temp_log_file)

        logger.log_prompt(sample_messages, model_info="test-model", iteration=5)

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()

            # Check for separators
            assert "=" * 80 in content
            # Check for timestamp
            assert "Timestamp:" in content
            # Check for model info
            assert "test-model" in content
            # Check for iteration
            assert "iteration 5" in content

    def test_log_prompt_appends_to_existing_file(
        self, temp_log_file: str, sample_messages: list
    ) -> None:
        r"""Test that logging appends to existing file instead of overwriting."""
        logger = PromptLogger(temp_log_file)

        logger.log_prompt(sample_messages, model_info="model-1")
        logger.log_prompt(sample_messages, model_info="model-2")

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()

            # Both entries should be present
            assert "PROMPT #1" in content
            assert "PROMPT #2" in content
            assert "model-1" in content
            assert "model-2" in content

    def test_log_prompt_with_complex_messages(
        self, temp_log_file: str
    ) -> None:
        r"""Test logging with complex nested message structures."""
        logger = PromptLogger(temp_log_file)

        complex_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
                ],
            },
        ]

        counter = logger.log_prompt(complex_messages)

        assert counter == 1

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Verify complex structure is preserved
            assert "image_url" in content
            assert "https://example.com/image.jpg" in content
