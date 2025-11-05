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
from typing import List
from unittest.mock import Mock

import pytest

from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.types import ModelType
from camel.utils.message_summarizer import MessageSummarizer, MessageSummary


@pytest.fixture
def sample_messages() -> List[BaseMessage]:
    r"""Create a list of sample messages for testing."""
    return [
        BaseMessage.make_user_message(
            role_name="User",
            content="I want to build a web application"
            " using Python and Flask.",
        ),
        BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "Great choice! Flask is a lightweight web framework. "
                "Let's start by setting up the basic project structure."
            ),
        ),
        BaseMessage.make_user_message(
            role_name="User",
            content="What are the key components we need?",
        ),
        BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "We'll need: 1) Flask for the web framework,"
                " 2) SQLAlchemy for database ORM,"
                " 3) HTML templates, and"
                " 4) CSS for styling."
            ),
        ),
    ]


@pytest.fixture
def mock_model_backend():
    r"""Create a mock model backend for testing."""
    mock_backend = Mock(spec=BaseModelBackend)
    mock_backend.model_type = ModelType.GPT_4O_MINI
    return mock_backend


def test_message_summarizer_initialization(mock_model_backend):
    r"""Test the initialization of MessageSummarizer."""
    # Test with custom model backend
    summarizer = MessageSummarizer(model_backend=mock_model_backend)
    assert summarizer.model_backend is mock_model_backend


def test_summarize_empty_messages(mock_model_backend):
    r"""Test summarizing an empty list of messages raises ValueError."""
    summarizer = MessageSummarizer(model_backend=mock_model_backend)
    with pytest.raises(
        ValueError, match="Cannot summarize an empty list of messages"
    ):
        summarizer.summarize([])


def test_summarize_single_message(mock_model_backend):
    r"""Test summarizing a single message."""
    message = BaseMessage.make_user_message(
        role_name="User",
        content="Let's build a Python web application.",
    )
    summarizer = MessageSummarizer(model_backend=mock_model_backend)

    # Mock the agent.step method to return a structured response
    mock_response = Mock()
    mock_msg = Mock()
    mock_summary = MessageSummary(
        summary="User wants to build a Python web application.",
        participants=["User"],
        key_topics_and_entities=["Python", "web application"],
        decisions_and_outcomes=["Build a web application"],
        action_items=[],
        progress_on_main_task="Planning phase",
    )
    mock_msg.parsed = mock_summary
    mock_response.msg = mock_msg
    summarizer.agent.step = Mock(return_value=mock_response)

    summary = summarizer.summarize([message])

    assert isinstance(summary, MessageSummary)
    assert "User" in summary.participants
    assert any(
        "Python" in entity for entity in summary.key_topics_and_entities
    )
    assert any(
        "web application" in entity.lower()
        for entity in summary.key_topics_and_entities
    )


def test_summarize_with_special_characters(mock_model_backend):
    r"""Test summarizing messages with special characters."""
    messages = [
        BaseMessage.make_user_message(
            role_name="User",
            content=(
                "Let's discuss the project's API endpoints"
                ": /api/v1/users and /api/v1/posts"
            ),
        ),
        BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "We'll implement these endpoints using"
                " Flask's @app.route decorator."
            ),
        ),
    ]
    summarizer = MessageSummarizer(model_backend=mock_model_backend)

    # Mock the agent.step method to return a structured response
    mock_response = Mock()
    mock_msg = Mock()
    mock_summary = MessageSummary(
        summary="Discussion about API endpoints and Flask implementation.",
        participants=["User", "Assistant"],
        key_topics_and_entities=["API endpoints", "Flask", "@app.route"],
        decisions_and_outcomes=["Implement API endpoints"],
        action_items=[],
        progress_on_main_task="Designing API structure",
    )
    mock_msg.parsed = mock_summary
    mock_response.msg = mock_msg
    summarizer.agent.step = Mock(return_value=mock_response)

    summary = summarizer.summarize(messages)

    assert isinstance(summary, MessageSummary)
    assert "User" in summary.participants
    assert "Assistant" in summary.participants
    assert any(
        "api" in entity.lower() for entity in summary.key_topics_and_entities
    )
    assert any(
        "endpoints" in entity.lower()
        for entity in summary.key_topics_and_entities
    )


def test_message_summarizer_with_custom_model_backend():
    r"""Test MessageSummarizer with a custom model backend."""
    # Create a mock model backend
    mock_backend = Mock(spec=BaseModelBackend)
    mock_backend.model_type = ModelType.GPT_4_1_MINI

    summarizer = MessageSummarizer(model_backend=mock_backend)
    assert summarizer.model_backend is mock_backend

    # Test that it still works with messages
    message = BaseMessage.make_user_message(
        role_name="User",
        content="Test message for custom model backend.",
    )

    # Mock the agent.step method
    mock_response = Mock()
    mock_msg = Mock()
    mock_summary = MessageSummary(
        summary="Testing custom model backend functionality.",
        participants=["User"],
        key_topics_and_entities=["Test message"],
        decisions_and_outcomes=["Testing custom backend"],
        action_items=[],
        progress_on_main_task="Testing phase",
    )
    mock_msg.parsed = mock_summary
    mock_response.msg = mock_msg
    summarizer.agent.step = Mock(return_value=mock_response)

    summary = summarizer.summarize([message])
    assert isinstance(summary, MessageSummary)


def test_summarize_messages(
    sample_messages: List[BaseMessage], mock_model_backend
):
    r"""Test the summarize method with sample messages."""
    summarizer = MessageSummarizer(model_backend=mock_model_backend)

    # Mock the agent.step method to return a structured response
    mock_response = Mock()
    mock_msg = Mock()
    mock_summary = MessageSummary(
        summary="Discussion about building a Python web application with "
        "Flask.",
        participants=["User", "Assistant"],
        key_topics_and_entities=[
            "Flask",
            "Python",
            "web framework",
            "SQLAlchemy",
        ],
        decisions_and_outcomes=[
            "Use Flask for web framework",
            "Include SQLAlchemy for ORM",
        ],
        action_items=[],
        progress_on_main_task="Planning and setup phase",
    )
    mock_msg.parsed = mock_summary
    mock_response.msg = mock_msg
    summarizer.agent.step = Mock(return_value=mock_response)

    summary = summarizer.summarize(sample_messages)

    # Verify the summary structure
    assert isinstance(summary, MessageSummary)
    assert isinstance(summary.participants, list)
    assert isinstance(summary.key_topics_and_entities, list)
    assert isinstance(summary.decisions_and_outcomes, list)
    assert isinstance(summary.progress_on_main_task, str)
    assert isinstance(summary.action_items, list)

    # Verify content
    assert len(summary.participants) > 0
    assert len(summary.key_topics_and_entities) > 0
    assert len(summary.decisions_and_outcomes) > 0
    assert len(summary.progress_on_main_task) > 0
    assert len(summary.summary) > 0

    # Verify specific content based on sample messages
    assert "User" in summary.participants
    assert "Assistant" in summary.participants
    assert any("Flask" in entity for entity in summary.key_topics_and_entities)


if __name__ == "__main__":
    pytest.main([__file__])
