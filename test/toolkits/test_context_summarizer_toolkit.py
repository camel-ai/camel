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

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from camel.agents import ChatAgent
from camel.memories import MemoryRecord
from camel.memories.records import ContextRecord
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend
from camel.toolkits.context_summarizer_toolkit import ContextSummarizerToolkit
from camel.types import RoleType
from camel.types.enums import OpenAIBackendRole


@pytest.fixture(scope="function")
def temp_directory():
    r"""Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def mock_agent():
    r"""Create a mock ChatAgent for testing."""
    agent = MagicMock(spec=ChatAgent)
    agent.agent_id = "test_agent_001"

    # Create a mock model backend that behaves like a real one
    mock_model = MagicMock(spec=BaseModelBackend)
    mock_model.token_counter = MagicMock()
    mock_model.token_limit = 1000
    agent.model_backend = mock_model

    agent.memory = MagicMock()
    agent.clear_memory = MagicMock()
    agent.update_memory = MagicMock()
    return agent


@pytest.fixture(scope="function")
def sample_messages():
    r"""Create sample messages for testing."""
    messages = []

    # Create a conversation about travel planning
    user_msg1 = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict={},
        content="Hello my name is John. I'm planning a trip to Japan in "
        "spring. What are the best cities to visit?",
    )

    assistant_msg1 = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content="Japan in the spring is a beautiful time to visit. Here are "
        "some of the best cities: Tokyo, Kyoto, Osaka, and Hiroshima.",
    )

    user_msg2 = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict={},
        content="What's the best way to travel between cities in Japan?",
    )

    assistant_msg2 = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content="The best way to travel between cities in Japan is by "
        "Shinkansen (bullet train). Consider getting a JR Pass for "
        "multiple cities.",
    )

    messages.extend([user_msg1, assistant_msg1, user_msg2, assistant_msg2])
    return messages


@pytest.fixture(scope="function")
def sample_memory_records(sample_messages):
    r"""Create sample memory records from messages."""
    records = []
    for msg in sample_messages:
        backend_role = (
            OpenAIBackendRole.USER
            if msg.role_type == RoleType.USER
            else OpenAIBackendRole.ASSISTANT
        )
        record = MemoryRecord(
            message=msg,
            role_at_backend=backend_role,
            agent_id="test_agent_001",
        )
        records.append(record)
    return records


@pytest.fixture(scope="function")
def sample_context_records(sample_memory_records):
    r"""Create sample context records for testing."""
    context_records = []
    for record in sample_memory_records:
        context_record = ContextRecord(memory_record=record, score=1.0)
        context_records.append(context_record)
    return context_records


@pytest.fixture(scope="function")
def context_summarizer_toolkit_fixture(mock_agent, temp_directory):
    r"""Create a ContextSummarizerToolkit instance for testing."""
    with patch('camel.agents.ChatAgent') as mock_chat_agent:
        # Create a mock summary agent
        mock_summary_agent = MagicMock()
        mock_summary_agent.agent_id = f"{mock_agent.agent_id}_summarizer"
        mock_summary_agent.reset = MagicMock()
        mock_summary_agent.step = MagicMock()
        mock_chat_agent.return_value = mock_summary_agent

        toolkit = ContextSummarizerToolkit(
            agent=mock_agent,
            working_directory=temp_directory,
        )
        return toolkit


def test_toolkit_initialization(
    context_summarizer_toolkit_fixture, temp_directory
):
    r"""Test that the toolkit initializes correctly."""
    toolkit = context_summarizer_toolkit_fixture
    assert toolkit.agent is not None
    assert (
        toolkit.working_directory.parent.resolve()
        == Path(temp_directory).resolve()
    )
    assert toolkit.session_id is not None
    assert toolkit.summary_filename == "agent_memory_summary"
    assert toolkit.history_filename == "agent_memory_history"
    assert toolkit.working_directory.exists()


def test_summary_saves_to_markdown_files(
    context_summarizer_toolkit_fixture, sample_context_records
):
    r"""Test that agent correctly saves summary in two .md files."""
    toolkit = context_summarizer_toolkit_fixture

    # Mock the agent's memory retrieve method
    toolkit.agent.memory.retrieve.return_value = sample_context_records

    # Mock the summary agent response
    mock_response = MagicMock()
    mock_response.msgs = [MagicMock()]
    mock_response.msgs[0].content = (
        "Summary: John is planning a trip to Japan in spring. We "
        "discussed cities like Tokyo, Kyoto, and transportation via "
        "Shinkansen."
    )

    with patch.object(
        toolkit.summary_agent, 'step', return_value=mock_response
    ):
        # Call the summarization function
        result = toolkit.summarize_full_conversation_history()

        # Check that the function completed successfully
        assert "Full context summarized" in result

        # Check that both files exist
        summary_file = toolkit.working_directory / "agent_memory_summary.md"
        history_file = toolkit.working_directory / "agent_memory_history.md"

        assert summary_file.exists(), "Summary file should be created"
        assert history_file.exists(), "History file should be created"

        # Read and verify summary file content
        summary_content = summary_file.read_text(encoding="utf-8")
        assert "# Conversation Summary:" in summary_content
        assert "Session ID:" in summary_content
        assert "John is planning a trip to Japan" in summary_content

        # Read and verify history file content
        history_content = history_file.read_text(encoding="utf-8")
        assert "# Conversation History:" in history_content
        assert "Total Messages: 4" in history_content
        assert "Japan in spring" in history_content
        assert "Shinkansen" in history_content
        assert "Message 1 - User" in history_content
        assert "Message 2 - Assistant" in history_content


def test_conversation_history_removal_and_summary_push(
    context_summarizer_toolkit_fixture, sample_context_records
):
    r"""Test that agent removes conversation history and pushes summary."""
    toolkit = context_summarizer_toolkit_fixture

    # Setup mock agent memory
    toolkit.agent.memory.retrieve.return_value = sample_context_records

    # Mock the summary agent response
    mock_response = MagicMock()
    mock_response.msgs = [MagicMock()]
    summary_text = (
        "Summary: John is planning Japan trip. Discussed Tokyo, Kyoto, "
        "Shinkansen transport."
    )
    mock_response.msgs[0].content = summary_text

    with patch.object(
        toolkit.summary_agent, 'step', return_value=mock_response
    ):
        # Call summarization
        result = toolkit.summarize_full_conversation_history()

        # Verify that clear_memory was called (history removal)
        toolkit.agent.clear_memory.assert_called_once()

        # Verify that update_memory was called with summary (summary push)
        toolkit.agent.update_memory.assert_called_once()

        # Check the arguments passed to update_memory
        call_args = toolkit.agent.update_memory.call_args
        summary_message = call_args[0][0]  # First argument (message)
        backend_role = call_args[0][1]  # Second argument (role)

        # Verify the summary message content
        assert (
            "[Context Summary from Previous Conversation]"
            in summary_message.content
        )
        assert summary_text in summary_message.content
        assert backend_role == OpenAIBackendRole.USER

        # Verify successful completion
        assert "Full context summarized" in result


def test_keyword_search_functionality(
    context_summarizer_toolkit_fixture, sample_context_records
):
    r"""Test that agent correctly searches conversation history."""
    toolkit = context_summarizer_toolkit_fixture

    # Setup the toolkit with sample data first
    toolkit.agent.memory.retrieve.return_value = sample_context_records

    # Create history file with sample data
    mock_response = MagicMock()
    mock_response.msgs = [MagicMock()]
    mock_response.msgs[0].content = "Test summary for search."

    with patch.object(
        toolkit.summary_agent, 'step', return_value=mock_response
    ):
        # First save the conversation to create history file
        toolkit.summarize_full_conversation_history()

    # Test keyword search
    search_keywords = ["Japan", "travel", "Tokyo"]
    search_result = toolkit.search_full_conversation_history(
        keywords=search_keywords, top_k=2
    )

    # Verify search results format
    assert "Found relevant conversation excerpts" in search_result
    assert "Japan, travel, Tokyo" in search_result
    assert "Search Results" in search_result
    assert "keyword matches:" in search_result

    # Test with keywords that should match our sample data
    japan_results = toolkit.search_full_conversation_history(
        keywords=["Japan", "spring"], top_k=3
    )
    assert "Japan, spring" in japan_results
    assert "Message" in japan_results

    # Test with keywords that won't match
    no_match_results = toolkit.search_full_conversation_history(
        keywords=["Python", "coding"], top_k=2
    )
    assert "No relevant conversations found" in no_match_results


def test_memory_info_functionality(
    context_summarizer_toolkit_fixture, sample_context_records
):
    r"""Test memory info reporting functionality."""
    toolkit = context_summarizer_toolkit_fixture

    # Setup mock memory
    toolkit.agent.memory.retrieve.return_value = sample_context_records

    # Get memory info
    info_result = toolkit.get_conversation_memory_info()

    # Verify info format
    assert "Current messages in memory: 4" in info_result
    assert "Save directory:" in info_result
    assert "Summary file:" in info_result
    assert "History file:" in info_result
    assert "Text search: Enabled" in info_result


def test_should_compress_context(
    context_summarizer_toolkit_fixture, sample_context_records
):
    r"""Test context compression decision logic."""
    toolkit = context_summarizer_toolkit_fixture

    # Setup mock memory
    toolkit.agent.memory.retrieve.return_value = sample_context_records

    # Test with low message limit - should compress
    should_compress_low = toolkit.should_compress_context(message_limit=2)
    assert should_compress_low is True

    # Test with high message limit - should not compress
    should_compress_high = toolkit.should_compress_context(message_limit=10)
    assert should_compress_high is False

    # Test with token limit
    toolkit.agent.memory.get_context.return_value = ("context", 500)
    should_compress_tokens = toolkit.should_compress_context(
        message_limit=10, token_limit=400
    )
    assert should_compress_tokens is True


def test_over_compression_prevention(
    context_summarizer_toolkit_fixture, sample_memory_records
):
    r"""Test that over-compression is prevented."""
    toolkit = context_summarizer_toolkit_fixture

    # Mock summary agent
    mock_response = MagicMock()
    mock_response.msgs = [MagicMock()]
    mock_response.msgs[0].content = "First summary"

    with patch.object(
        toolkit.summary_agent, 'step', return_value=mock_response
    ):
        # First summarization
        first_summary = toolkit._summarize_messages(sample_memory_records)
        assert "First summary" in first_summary

        # Second attempt should return existing summary
        second_summary = toolkit._summarize_messages(sample_memory_records)
        assert second_summary == "First summary"


def test_empty_memory_handling(context_summarizer_toolkit_fixture):
    r"""Test handling of empty conversation memory."""
    toolkit = context_summarizer_toolkit_fixture

    # Setup empty memory
    toolkit.agent.memory.retrieve.return_value = []

    # Test summarization with empty memory
    result = toolkit.summarize_full_conversation_history()
    assert "No conversation history found" in result


if __name__ == "__main__":
    import sys

    pytest.main([sys.argv[0]])
