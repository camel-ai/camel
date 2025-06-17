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

import pytest

from camel.messages import BaseMessage
from camel.types import ModelType
from camel.utils.message_summarizer import MessageSummarizer, SummarySchema


@pytest.fixture
def sample_messages() -> List[BaseMessage]:
    """Create a list of sample messages for testing."""
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


def test_message_summarizer_initialization():
    """Test the initialization of MessageSummarizer."""
    # Test with default model
    summarizer = MessageSummarizer()
    assert summarizer.model_backend.model_type == ModelType.GPT_4O_MINI

    # Test with custom model
    custom_model = ModelType.GPT_4_1_MINI
    summarizer = MessageSummarizer(model=custom_model)
    assert summarizer.model_backend.model_type == custom_model


def test_summarize_messages(sample_messages: List[BaseMessage]):
    """Test the summarize method with sample messages."""
    summarizer = MessageSummarizer()
    summary = summarizer.summarize(sample_messages)
    print(f"\n~~Summary for test_summarize_messages: {summary}")

    # Verify the summary structure
    assert isinstance(summary, SummarySchema)
    assert isinstance(summary.roles, list)
    assert isinstance(summary.key_entities, list)
    assert isinstance(summary.decisions, list)
    assert isinstance(summary.task_progress, str)
    assert isinstance(summary.context, str)

    # Verify content
    assert len(summary.roles) > 0
    assert len(summary.key_entities) > 0
    assert len(summary.decisions) > 0
    assert len(summary.task_progress) > 0
    assert len(summary.context) > 0

    # Verify specific content based on sample messages
    assert "User" in summary.roles
    assert "Assistant" in summary.roles
    assert any("Flask" in entity for entity in summary.key_entities)


def test_summarize_empty_messages():
    """Test summarizing an empty list of messages."""
    summarizer = MessageSummarizer()
    summary = summarizer.summarize([])
    print(f"\n~~Summary2: {summary}")

    assert isinstance(summary, SummarySchema)
    assert len(summary.roles) == 0
    assert len(summary.key_entities) == 0
    assert len(summary.decisions) == 0
    assert len(summary.task_progress) == 0
    assert len(summary.context) == 0


def test_summarize_single_message():
    """Test summarizing a single message."""
    message = BaseMessage.make_user_message(
        role_name="User",
        content="Let's build a Python web application.",
    )
    summarizer = MessageSummarizer()
    summary = summarizer.summarize([message])
    print(f"\n~~Summary3: {summary}")

    assert isinstance(summary, SummarySchema)
    assert "User" in summary.roles
    assert any("Python" in entity for entity in summary.key_entities)
    assert any(
        "web application" in entity.lower() for entity in summary.key_entities
    )


def test_summarize_with_special_characters():
    """Test summarizing messages with special characters."""
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
    summarizer = MessageSummarizer()
    summary = summarizer.summarize(messages)
    print(f"\n~~Summary4: {summary}")

    assert isinstance(summary, SummarySchema)
    assert "User" in summary.roles
    assert "Assistant" in summary.roles
    assert any("api" in entity.lower() for entity in summary.key_entities)
    assert any(
        "endpoints" in entity.lower() for entity in summary.key_entities
    )


if __name__ == "__main__":
    pytest.main([__file__])
