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

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ChatCompletion, ModelPlatformType, ModelType


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_model_response():
    """Create a mock model response for testing."""
    return ChatCompletion(
        id="mock_compression_id",
        choices=[
            Choice(
                finish_reason='stop',
                index=0,
                logprobs=None,
                message=ChatCompletionMessage(
                    content="Test summary of conversation.",
                    role='assistant',
                    function_call=None,
                    tool_calls=None,
                ),
            )
        ],
        created=123456,
        model='gpt-4o-mini',
        object='chat.completion',
        system_fingerprint='fp_test',
        usage=CompletionUsage(
            completion_tokens=10, prompt_tokens=50, total_tokens=60
        ),
    )


@pytest.fixture
def compression_agent(temp_memory_dir, mock_model_response):
    """Create a ChatAgent with auto-compression enabled for testing."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    agent = ChatAgent(
        system_message="You are a test assistant.",
        model=model,
        agent_id="test_compression_agent",
        auto_compress_context=True,
        memory_save_directory=str(temp_memory_dir),
        compress_message_limit=3,  # Low limit for testing
    )

    # Mock the model backend to avoid actual LLM calls
    agent.model_backend.run = MagicMock(return_value=mock_model_response)

    return agent


def test_agent_initialization_with_compression(
    compression_agent, temp_memory_dir
):
    """Test that agent initializes correctly with compression settings."""
    agent = compression_agent

    assert agent.auto_compress_context is True
    assert agent.compress_message_limit == 3
    assert str(temp_memory_dir) in agent.memory_save_directory
    assert hasattr(agent, '_context_compression_service')


def test_memory_compression_trigger(compression_agent):
    """Test that memory compression is triggered after reaching message
    limit."""
    agent = compression_agent

    # Add messages up to the limit
    for i in range(3):
        user_msg = f"Test message {i+1}"
        response = agent.step(user_msg)
        assert len(response.msgs) > 0

    # Verify memory has been compressed (should have summary + current message)
    memory_records = agent.memory.retrieve()
    # After compression, should have fewer than original messages
    assert len(memory_records) <= 3


def test_compression_service_creates_files(compression_agent, temp_memory_dir):
    """Test that compression service creates summary and history files."""
    agent = compression_agent

    # Trigger compression by adding enough messages
    for i in range(4):
        user_msg = f"Message to trigger compression {i+1}"
        agent.step(user_msg)

    # Check that session directory and files are created
    session_dirs = [
        d
        for d in temp_memory_dir.iterdir()
        if d.is_dir() and d.name.startswith("session_")
    ]
    assert len(session_dirs) >= 1

    session_dir = session_dirs[0]
    assert (session_dir / "summary.md").exists()
    assert (session_dir / "history.md").exists()


def test_refresh_context_with_summary(compression_agent):
    """Test that agent context is refreshed with summary after compression."""
    agent = compression_agent
    initial_memory_count = len(agent.memory.retrieve())

    # Trigger compression
    for i in range(4):
        user_msg = f"Context refresh test {i+1}"
        agent.step(user_msg)

    # Memory should contain the summary
    current_records = agent.memory.retrieve()

    # Should have summary message in memory
    summary_found = any(
        "summary" in str(record.memory_record.message.content).lower()
        for record in current_records
    )
    assert summary_found or len(current_records) <= initial_memory_count + 2


def test_compression_without_auto_trigger(
    temp_memory_dir, mock_model_response
):
    """Test agent behavior when auto-compression is disabled."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    agent = ChatAgent(
        system_message="You are a test assistant.",
        model=model,
        agent_id="test_no_compression_agent",
        auto_compress_context=False,  # Disabled
        memory_save_directory=str(temp_memory_dir),
        compress_message_limit=3,
    )

    agent.model_backend.run = MagicMock(return_value=mock_model_response)

    # Add messages beyond the limit
    for i in range(5):
        user_msg = f"No compression message {i+1}"
        agent.step(user_msg)

    # Memory should contain all messages (no compression triggered)
    memory_records = agent.memory.retrieve()
    assert len(memory_records) >= 5


def test_multiple_compression_cycles(compression_agent):
    """Test that multiple compression cycles work correctly."""
    agent = compression_agent

    # First compression cycle
    for i in range(4):
        user_msg = f"First cycle message {i+1}"
        agent.step(user_msg)

    first_memory_count = len(agent.memory.retrieve())

    # Second compression cycle
    for i in range(4):
        user_msg = f"Second cycle message {i+1}"
        agent.step(user_msg)

    second_memory_count = len(agent.memory.retrieve())

    # Memory should be managed across multiple compression cycles
    assert second_memory_count <= first_memory_count + 3


def test_compression_service_summary_content(
    compression_agent, temp_memory_dir
):
    """Test that compression service generates proper summary content."""
    agent = compression_agent

    # Add specific content to test summarization
    test_messages = [
        "Hello, I need help with data analysis.",
        "I want to analyze customer sales data.",
        "Please help me create a Python script.",
        "Thank you for your assistance.",
    ]

    for msg in test_messages:
        agent.step(msg)

    # Find the created session directory
    session_dirs = [
        d
        for d in temp_memory_dir.iterdir()
        if d.is_dir() and d.name.startswith("session_")
    ]
    assert len(session_dirs) >= 1

    session_dir = session_dirs[0]
    summary_file = session_dir / "summary.md"

    if summary_file.exists():
        summary_content = summary_file.read_text()
        assert "Conversation Summary" in summary_content
        assert "Metadata" in summary_content
        assert "Session ID" in summary_content
