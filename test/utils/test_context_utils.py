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
from unittest.mock import MagicMock

import pytest

from camel.agents import ChatAgent
from camel.models import BaseModelBackend
from camel.utils.context_utils import ContextUtility


@pytest.fixture(scope="function")
def temp_directory():
    r"""Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def mock_agent():
    r"""Create a mock ChatAgent for testing."""
    from camel.messages import BaseMessage
    from camel.types import RoleType

    agent = MagicMock(spec=ChatAgent)
    agent.agent_id = "test_agent_001"

    # Create a mock model backend
    mock_model = MagicMock(spec=BaseModelBackend)
    agent.model_backend = mock_model

    # Create mock system message
    mock_system_message = MagicMock(spec=BaseMessage)
    mock_system_message.content = "You are a helpful assistant."
    mock_system_message.role_name = "Assistant"
    mock_system_message.role_type = RoleType.ASSISTANT
    mock_system_message.meta_dict = {}

    def create_new_instance_side_effect(new_content):
        new_mock = MagicMock(spec=BaseMessage)
        new_mock.content = new_content
        new_mock.role_name = "Assistant"
        new_mock.role_type = RoleType.ASSISTANT
        new_mock.meta_dict = {}
        new_mock.create_new_instance = MagicMock(
            side_effect=create_new_instance_side_effect
        )
        return new_mock

    mock_system_message.create_new_instance = MagicMock(
        side_effect=create_new_instance_side_effect
    )

    # Set up required attributes
    agent._original_system_message = mock_system_message
    agent._system_message = mock_system_message
    agent.system_message = mock_system_message

    # Create mock memory with clear method
    mock_memory = MagicMock()
    mock_memory.clear = MagicMock()
    agent.memory = mock_memory

    agent.update_memory = MagicMock()
    agent.clear_memory = MagicMock()
    return agent


@pytest.fixture(scope="function")
def context_utility_fixture(temp_directory):
    r"""Create a ContextUtility instance for testing."""
    return ContextUtility(working_directory=temp_directory)


def test_load_markdown_context_to_memory_preserves_existing_conversation(
    mock_agent, context_utility_fixture
):
    r"""Test that load_markdown_context_to_memory preserves existing memory."""
    context_util = context_utility_fixture

    # Create test context content
    context_content = """# Previous Workflow Summary

## Task Completed
Data analysis of customer sales using pandas and matplotlib.

## Key Findings  
- Sales increased 15% in Q4
- Electronics is top category
- Customer retention: 85%
"""

    # Save context file using ContextUtility
    context_util.save_markdown_file(
        filename="test_workflow",
        content=context_content,
        title="Test Workflow Context",
    )

    # Load context into agent memory
    result = context_util.load_markdown_context_to_memory(
        agent=mock_agent, filename="test_workflow"
    )

    # Verify successful loading
    assert "Context appended to agent" in result
    assert "characters)" in result

    # Verify that update_memory was called (but NOT clear_memory)
    mock_agent.update_memory.assert_called_once()
    mock_agent.clear_memory.assert_not_called()

    # Check the message content and role
    call_args = mock_agent.update_memory.call_args
    context_message = call_args[0][0]  # First argument (message)
    backend_role = call_args[0][1]  # Second argument (role)

    # Verify the context message format
    assert (
        "The following is the context from a previous"
        in context_message.content
    )
    assert "Data analysis of customer sales" in context_message.content
    assert "Sales increased 15%" in context_message.content
    assert backend_role.value == "system"


def test_load_markdown_context_to_memory_file_not_found(
    mock_agent, context_utility_fixture
):
    r"""Test handling of non-existent context files."""
    context_util = context_utility_fixture

    # Try to load non-existent file
    result = context_util.load_markdown_context_to_memory(
        agent=mock_agent, filename="nonexistent_file"
    )

    # Verify error handling
    assert "Context file not found or empty" in result

    # Verify no memory operations occurred
    mock_agent.update_memory.assert_not_called()
    mock_agent.clear_memory.assert_not_called()


def test_load_markdown_context_to_memory_empty_file(
    mock_agent, context_utility_fixture
):
    r"""Test handling of empty context files."""
    context_util = context_utility_fixture

    # Create truly empty file by writing directly to filesystem
    empty_file = context_util.working_directory / "empty_context.md"
    empty_file.write_text("", encoding="utf-8")

    # Try to load empty file
    result = context_util.load_markdown_context_to_memory(
        agent=mock_agent, filename="empty_context"
    )

    # Verify error handling
    assert "Context file not found or empty" in result

    # Verify no memory operations occurred
    mock_agent.update_memory.assert_not_called()


def test_load_markdown_context_to_memory_with_workflow_content(
    mock_agent, context_utility_fixture
):
    r"""Test loading workflow context with multiple agents and tools."""
    context_util = context_utility_fixture

    # Create workflow context
    workflow_content = """## Multi-Agent Workflow

### Agents Involved
- Agent A: Data collection using web_toolkit
- Agent B: Analysis using pandas_toolkit  
- Agent C: Reporting using email_toolkit

### Results
Successfully processed 10,000 records and sent reports.

### Next Steps
- Automate the pipeline
- Add error handling
"""

    # Save workflow context
    context_util.save_markdown_file(
        filename="multi_agent_workflow", content=workflow_content
    )

    # Load into agent memory
    result = context_util.load_markdown_context_to_memory(
        agent=mock_agent, filename="multi_agent_workflow"
    )

    # Verify successful loading
    assert "Context appended to agent" in result

    # Check that workflow details are preserved
    call_args = mock_agent.update_memory.call_args
    context_message = call_args[0][0]

    assert "Multi-Agent Workflow" in context_message.content
    assert "web_toolkit" in context_message.content
    assert "pandas_toolkit" in context_message.content
    assert "10,000 records" in context_message.content


def test_context_utility_initialization(temp_directory):
    r"""Test ContextUtility initialization."""
    context_util = ContextUtility(working_directory=temp_directory)

    assert (
        context_util.working_directory.parent.resolve()
        == Path(temp_directory).resolve()
    )
    assert context_util.session_id is not None
    assert context_util.working_directory.exists()


def test_save_and_load_markdown_file(context_utility_fixture):
    r"""Test saving and loading markdown files."""
    context_util = context_utility_fixture

    # Test content
    test_content = "This is test content for markdown file."

    # Save file
    result = context_util.save_markdown_file(
        filename="test_file", content=test_content, title="Test Title"
    )

    assert result == "success"

    # Load file
    loaded_content = context_util.load_markdown_file("test_file")

    assert "Test Title" in loaded_content
    assert test_content in loaded_content


if __name__ == "__main__":
    import sys

    pytest.main([sys.argv[0]])
