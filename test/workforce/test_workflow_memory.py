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

import os
import tempfile
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.societies.workforce import Workforce
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.tasks.task import Task, TaskState


class MockSingleAgentWorker(SingleAgentWorker):
    """A mock worker for testing workflow functionality."""

    def __init__(self, description: str):
        # Create a mock agent with conversation history
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker",
            content=f"You are a {description} for testing.",
        )
        agent = ChatAgent(sys_msg)
        super().__init__(description, agent)

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        """Mock task processing with simulated conversation."""
        # Simulate some conversation history
        user_msg = BaseMessage.make_user_message(
            role_name="User", content=f"Please process: {task.content}"
        )
        assistant_msg = BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=f"Processed task: {task.content} successfully",
        )

        # Record conversation to create some history for summarization
        self.worker.record_message(user_msg)
        self.worker.record_message(assistant_msg)

        task.result = f"Successfully processed: {task.content}"
        task.state = TaskState.DONE
        return TaskState.DONE


@pytest.fixture
def temp_context_dir():
    """Create a temporary directory for context files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch.dict(os.environ, {"CAMEL_WORKDIR": temp_dir}):
            yield temp_dir


@pytest.fixture
def mock_workforce():
    """Create a workforce with mock SingleAgentWorker instances."""
    workforce = Workforce("Test Workforce")

    # Add mock workers with different descriptions
    analyst_worker = MockSingleAgentWorker("data_analyst")
    developer_worker = MockSingleAgentWorker("python_developer")

    workforce._children = [analyst_worker, developer_worker]
    return workforce


class TestSingleAgentWorkerWorkflow:
    """Test workflow functionality for SingleAgentWorker."""

    def test_save_workflow_success(self, temp_context_dir):
        """Test successful workflow saving."""
        worker = MockSingleAgentWorker("test_analyst")

        # Mock the summarize method to return success
        mock_result = {
            "status": "success",
            "summary": "Test workflow summary",
            "file_path": (
                f"{temp_context_dir}/test_analyst_workflow_20250122.md"
            ),
        }

        with patch.object(
            worker.worker, 'summarize', return_value=mock_result
        ):
            result = worker.save_workflow_memories()

            assert result["status"] == "success"
            assert result["worker_description"] == "test_analyst"
            assert "test_analyst_workflow_" in result["file_path"]

    def test_save_workflow_non_chat_agent(self):
        """Test workflow saving with non-ChatAgent worker."""
        # Create worker and then replace worker with non-ChatAgent
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="Test"
        )
        worker = SingleAgentWorker("test", ChatAgent(sys_msg))

        # Replace the worker with a non-ChatAgent object
        worker.worker = "not_a_chat_agent"

        result = worker.save_workflow_memories()

        assert result["status"] == "error"
        assert "Worker must be a ChatAgent" in result["message"]
        assert result["worker_description"] == "test"

    def test_save_workflow_exception(self, temp_context_dir):
        """Test workflow saving when exception occurs."""
        worker = MockSingleAgentWorker("test_analyst")

        # Mock summarize to raise exception
        with patch.object(
            worker.worker, 'summarize', side_effect=Exception("Test error")
        ):
            result = worker.save_workflow_memories()

            assert result["status"] == "error"
            assert (
                "Failed to save workflow memories: Test error"
                in result["message"]
            )

    @patch('glob.glob')
    @patch('os.path.getmtime')
    def test_load_workflow_success(
        self, mock_getmtime, mock_glob, temp_context_dir
    ):
        """Test successful workflow loading (legacy pattern matching mode)."""
        worker = MockSingleAgentWorker("data_analyst")

        # Mock file discovery
        mock_files = [
            f"{temp_context_dir}/session_123/data_analyst_workflow_20250122.md"
        ]
        mock_glob.return_value = mock_files
        mock_getmtime.return_value = 1234567890

        # Mock the shared context utility methods
        mock_context_utility = MagicMock()
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        with patch(
            'camel.utils.context_utils.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            # Use legacy pattern matching mode
            result = worker.load_workflow_memories(use_smart_selection=False)

            assert result is True
            mock_context_utility.load_markdown_file.assert_called()

    def test_load_workflow_no_files(self, temp_context_dir):
        """Test workflow loading when no files found."""
        worker = MockSingleAgentWorker("data_analyst")

        with patch('glob.glob', return_value=[]):
            result = worker.load_workflow_memories()

            assert result is False

    def test_load_workflow_non_chat_agent(self):
        """Test workflow loading with non-ChatAgent worker."""
        # Create worker and then replace worker with non-ChatAgent
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="Test"
        )
        worker = SingleAgentWorker("test", ChatAgent(sys_msg))

        # Replace the worker with a non-ChatAgent object
        worker.worker = "not_a_chat_agent"

        result = worker.load_workflow_memories()

        assert result is False

    @patch('glob.glob')
    def test_load_workflow_prioritizes_newest_session(
        self, mock_glob, temp_context_dir
    ):
        """Test that workflow loading prioritizes files from newest sessions
        (legacy mode).

        This test verifies that when multiple workflow files exist across
        different sessions, files from the newest session (by session
        timestamp) are loaded first, regardless of file modification times.
        """
        worker = MockSingleAgentWorker("data_analyst")

        # Simulate realistic scenario: multiple workforce sessions over time
        # Each session has workflows from different agents
        # Session 1 (older): 17:23:56
        # Session 2 (newer): 17:46:50
        mock_files = [
            # Newer session files (data_analyst and other agents)
            f"{temp_context_dir}/workforce_workflows/session_20251002_174650_470517/data_analyst_workflow.md",
            f"{temp_context_dir}/workforce_workflows/session_20251002_174650_470517/developer_workflow.md",
            # Older session files (data_analyst and other agents)
            f"{temp_context_dir}/workforce_workflows/session_20251002_172356_365242/data_analyst_workflow.md",
            f"{temp_context_dir}/workforce_workflows/session_20251002_172356_365242/researcher_workflow.md",
        ]
        mock_glob.return_value = mock_files

        # Mock the shared context utility methods
        mock_context_utility = MagicMock()
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        with patch(
            'camel.utils.context_utils.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            # Use legacy pattern matching mode
            result = worker.load_workflow_memories(
                max_workflows=1, use_smart_selection=False
            )

            assert result is True

            # Verify load was called once
            assert mock_context_utility.load_markdown_file.call_count == 1

            # Get the filename that was loaded (first argument)
            loaded_filename = (
                mock_context_utility.load_markdown_file.call_args[0][0]
            )

            # The loaded file should be 'data_analyst_workflow' (without .md)
            # from the newer session (verified by it being loaded first)
            assert loaded_filename == "data_analyst_workflow"

    @patch('glob.glob')
    def test_load_workflow_memories_resets_system_message(
        self, mock_glob, temp_context_dir
    ):
        """Test that multiple calls to load_workflow_memories reset system
        message (legacy mode).

        This test verifies that calling load_workflow_memories multiple times
        doesn't accumulate workflow context but instead resets to original
        system message each time.
        """
        worker = MockSingleAgentWorker("data_analyst")

        # get original system message content
        original_content = worker.worker._original_system_message.content

        # mock workflow files
        mock_files = [
            f"{temp_context_dir}/workforce_workflows/session_1/data_analyst_workflow.md"
        ]
        mock_glob.return_value = mock_files

        # mock the shared context utility methods
        mock_context_utility = MagicMock()
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        with patch(
            'camel.utils.context_utils.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            # first call to load_workflow_memories (legacy mode)
            worker.load_workflow_memories(
                max_workflows=1, use_smart_selection=False
            )

            # verify reset was called (system message matches original)
            first_call_system_content = worker.worker._system_message.content

            # second call to load_workflow_memories (legacy mode)
            worker.load_workflow_memories(
                max_workflows=1, use_smart_selection=False
            )

            # after second call, system message should still be based on
            # original (not accumulating from first call)
            second_call_system_content = worker.worker._system_message.content

            # verify both calls resulted in same base system message
            # (indicating reset happened before each load)
            assert first_call_system_content == second_call_system_content

            # verify the system message contains original content
            assert original_content in second_call_system_content

            # verify load was called twice (once per load_workflow_memories)
            assert mock_context_utility.load_markdown_file.call_count == 2


class TestWorkforceWorkflowMemoryMethods:
    """Test workflow functionality for Workforce."""

    def test_save_workflow_memories_success(self, mock_workforce):
        """Test successful workflow saving for all workers."""
        # Mock save_workflow_memories for both workers
        mock_result_1 = {
            "status": "success",
            "file_path": "/path/to/data_analyst_workflow.md",
        }
        mock_result_2 = {
            "status": "success",
            "file_path": "/path/to/python_developer_workflow.md",
        }

        with (
            patch.object(
                mock_workforce._children[0],
                'save_workflow_memories',
                return_value=mock_result_1,
            ),
            patch.object(
                mock_workforce._children[1],
                'save_workflow_memories',
                return_value=mock_result_2,
            ),
        ):
            results = mock_workforce.save_workflow_memories()

            assert len(results) == 2
            assert all("/path/to/" in path for path in results.values())

    def test_save_workflow_memories_mixed_results(self, mock_workforce):
        """Test workflow saving with mixed success/failure results."""
        # Mock one success, one failure
        mock_result_success = {
            "status": "success",
            "file_path": "/path/to/data_analyst_workflow.md",
        }
        mock_result_error = {
            "status": "error",
            "message": "No conversation context",
        }

        with (
            patch.object(
                mock_workforce._children[0],
                'save_workflow_memories',
                return_value=mock_result_success,
            ),
            patch.object(
                mock_workforce._children[1],
                'save_workflow_memories',
                return_value=mock_result_error,
            ),
        ):
            results = mock_workforce.save_workflow_memories()

            assert len(results) == 2
            assert (
                "/path/to/data_analyst_workflow.md"
                in results[mock_workforce._children[0].node_id]
            )
            assert (
                "error: No conversation context"
                in results[mock_workforce._children[1].node_id]
            )

    def test_save_workflow_memories_exception(self, mock_workforce):
        """Test workflow saving when exception occurs."""
        with patch.object(
            mock_workforce._children[0],
            'save_workflow_memories',
            side_effect=Exception("Test error"),
        ):
            results = mock_workforce.save_workflow_memories()

            assert (
                "error: Test error"
                in results[mock_workforce._children[0].node_id]
            )

    def test_save_workflow_memories_real_execution(self, temp_context_dir):
        """Test save_workflow_memories with real internal execution.

        This test exercises the actual save_workflow_memories() implementation,
        only mocking the ChatAgent.summarize() method to avoid LLM API calls.

        Tests the following internal behavior:
        - Workforce iteration through child workers
        - SingleAgentWorker validation logic
        (_validate_workflow_save_requirements)
        - Context utility setup and agent configuration
        - Filename generation from worker description
        (_generate_workflow_filename)
        - Workflow prompt preparation (_prepare_workflow_prompt)
        - Agent selection for summarization (_select_agent_for_summarization)
        - Worker metadata addition to results
        - Result processing and error handling in Workforce
        - Shared context utility setup between Workforce and workers
        """
        workforce = Workforce("Test Workforce")
        worker = MockSingleAgentWorker("data_analyst")
        workforce._children = [worker]

        # Simulate some conversation history
        user_msg = BaseMessage.make_user_message(
            role_name="User", content="Analyze the sales data"
        )
        assistant_msg = BaseMessage.make_assistant_message(
            role_name="Assistant", content="Analysis complete"
        )
        worker.worker.record_message(user_msg)
        worker.worker.record_message(assistant_msg)

        # Store initial conversation accumulator state
        initial_accumulator = worker._conversation_accumulator

        # Mock only the ChatAgent.summarize() method (which makes LLM calls)
        mock_summary_result = {
            "status": "success",
            "summary": "Completed data analysis workflow",
            "file_path": (
                f"{temp_context_dir}/workforce_workflows/"
                "session_test/data_analyst_workflow.md"
            ),
            "worker_description": "data_analyst",
        }

        with patch.object(
            ChatAgent, 'summarize', return_value=mock_summary_result
        ) as mock_summarize:
            # This executes the real save_workflow_memories() logic
            results = workforce.save_workflow_memories()

            # Verify Workforce correctly processes worker results
            assert len(results) == 1
            assert worker.node_id in results
            assert "data_analyst_workflow" in results[worker.node_id]
            assert results[worker.node_id] == mock_summary_result["file_path"]

            # Verify shared context utility was set up correctly
            assert worker.worker._context_utility is not None

            # Verify ChatAgent.summarize was called with correct parameters
            # (validates filename generation, prompt preparation, agent
            # selection)
            mock_summarize.assert_called_once()
            call_kwargs = mock_summarize.call_args[1]

            # Verify filename generation includes worker description
            assert 'filename' in call_kwargs
            assert 'data_analyst_workflow' in call_kwargs['filename']

            # Verify structured output format is set (WorkflowSummary)
            assert 'response_format' in call_kwargs
            assert call_kwargs['response_format'] is not None

            # Verify summary prompt was prepared
            assert 'summary_prompt' in call_kwargs
            assert call_kwargs['summary_prompt'] is not None

            # Verify conversation accumulator cleanup
            # (it should be None after successful save)
            if initial_accumulator is not None:
                assert worker._conversation_accumulator is None

    def test_load_workflow_memories_success(self, mock_workforce):
        """Test successful workflow loading for all workers."""
        with (
            patch.object(
                mock_workforce._children[0],
                'load_workflow_memories',
                return_value=True,
            ),
            patch.object(
                mock_workforce._children[1],
                'load_workflow_memories',
                return_value=True,
            ),
        ):
            results = mock_workforce.load_workflow_memories()

            assert len(results) == 2
            assert all(success for success in results.values())

    def test_load_workflow_memories_mixed_results(self, mock_workforce):
        """Test workflow loading with mixed success/failure results."""
        with (
            patch.object(
                mock_workforce._children[0],
                'load_workflow_memories',
                return_value=True,
            ),
            patch.object(
                mock_workforce._children[1],
                'load_workflow_memories',
                return_value=False,
            ),
        ):
            results = mock_workforce.load_workflow_memories()

            assert results[mock_workforce._children[0].node_id] is True
            assert results[mock_workforce._children[1].node_id] is False

    def test_load_workflow_memories_exception(self, mock_workforce):
        """Test workflow loading when exception occurs."""
        with patch.object(
            mock_workforce._children[0],
            'load_workflow_memories',
            side_effect=Exception("Test error"),
        ):
            results = mock_workforce.load_workflow_memories()

            assert results[mock_workforce._children[0].node_id] is False

    def test_workflows_skip_non_single_agent_workers(self):
        """Test that workflow methods skip non-SingleAgentWorker instances."""
        from camel.societies.workforce.role_playing_worker import (
            RolePlayingWorker,
        )

        workforce = Workforce("Test Workforce")

        # Add a mock RolePlayingWorker (not SingleAgentWorker)
        mock_role_playing_worker = MagicMock(spec=RolePlayingWorker)
        mock_role_playing_worker.node_id = "role_playing_worker_123"
        workforce._children = [mock_role_playing_worker]

        # Test save_workflows
        save_results = workforce.save_workflow_memories()
        assert (
            "skipped: MagicMock not supported"
            in save_results[mock_role_playing_worker.node_id]
        )

        # Test load_workflows
        load_results = workforce.load_workflow_memories()
        assert load_results[mock_role_playing_worker.node_id] is False


class TestWorkflowIntegration:
    """Integration tests for workflow functionality."""

    def test_end_to_end_workflow_memory(self, temp_context_dir):
        """Test complete workflow: save workflow, load in new session."""
        # First session: create workforce and mock workflow saving
        workforce1 = Workforce("Test Team")
        worker1 = MockSingleAgentWorker("data_analyst")
        workforce1._children = [worker1]

        # Mock successful summarize and save
        mock_save_result = {
            "status": "success",
            "summary": "Data analysis workflow completed",
            "file_path": f"{temp_context_dir}/data_analyst_workflow_test.md",
        }

        with patch.object(
            worker1.worker, 'summarize', return_value=mock_save_result
        ):
            save_results = workforce1.save_workflow_memories()
            assert (
                save_results[worker1.node_id] == mock_save_result["file_path"]
            )

        # Second session: create new workforce and load workflows
        workforce2 = Workforce("Test Team")
        worker2 = MockSingleAgentWorker("data_analyst")
        workforce2._children = [worker2]

        # Mock successful workflow loading
        with patch.object(
            worker2, 'load_workflow_memories', return_value=True
        ):
            load_results = workforce2.load_workflow_memories()
            assert load_results[worker2.node_id] is True

    def test_filename_sanitization(self):
        """Test worker descriptions are properly sanitized for filenames."""
        worker = MockSingleAgentWorker("Data Analyst & ML Engineer!")

        # Mock datetime for consistent testing
        with patch(
            'camel.societies.workforce.single_agent_worker.datetime'
        ) as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = (
                "20250122_143022"
            )

            mock_result = {
                "status": "success",
                "summary": "Test summary",
                "file_path": (
                    "/path/to/data_analyst_ml_engineer_workflow_"
                    "20250122_143022.md"
                ),
            }

            with patch.object(
                worker.worker, 'summarize', return_value=mock_result
            ):
                # Verify the filename generation works with special characters
                result = worker.save_workflow_memories()
                assert result["status"] == "success"


class TestSharedContextUtility:
    """Test shared context utility functionality."""

    def test_get_workforce_shared_default(self):
        """Test getting default workforce shared context."""
        from camel.utils.context_utils import ContextUtility

        # Reset any existing shared sessions
        ContextUtility.reset_shared_sessions()

        # Get default shared context
        context1 = ContextUtility.get_workforce_shared()
        context2 = ContextUtility.get_workforce_shared()

        # Should return the same instance
        assert context1 is context2
        assert context1.session_id == context2.session_id

    def test_get_workforce_shared_specific_session(self):
        """Test getting workforce shared context with specific session ID."""
        from camel.utils.context_utils import ContextUtility

        # Reset any existing shared sessions
        ContextUtility.reset_shared_sessions()

        session_id = "test_session_123"

        # Get shared context with specific session
        context1 = ContextUtility.get_workforce_shared(session_id)
        context2 = ContextUtility.get_workforce_shared(session_id)

        # Should return the same instance
        assert context1 is context2
        assert context1.session_id == session_id
        assert context2.session_id == session_id

    def test_reset_shared_sessions(self):
        """Test resetting shared sessions."""
        from camel.utils.context_utils import ContextUtility

        # Create some shared contexts
        context1 = ContextUtility.get_workforce_shared()
        context2 = ContextUtility.get_workforce_shared("test_session")

        # Reset sessions
        ContextUtility.reset_shared_sessions()

        # Get new contexts - should be different instances
        new_context1 = ContextUtility.get_workforce_shared()
        new_context2 = ContextUtility.get_workforce_shared("test_session")

        assert new_context1 is not context1
        assert new_context2 is not context2

    def test_lazy_initialization_no_folder_creation(self):
        """Test that shared contexts don't create folders until needed."""
        import os
        import tempfile

        from camel.utils.context_utils import ContextUtility

        # Reset any existing shared sessions
        ContextUtility.reset_shared_sessions()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CAMEL_WORKDIR": temp_dir}):
                # Get shared context
                context = ContextUtility.get_workforce_shared()

                # Session directory should not exist yet
                session_dir = context.get_working_directory()
                assert not session_dir.exists()

                # Creating a file should create the directory
                context.save_markdown_file("test", "test content")
                assert session_dir.exists()

    def test_single_agent_worker_uses_shared_context(self):
        """Test that SingleAgentWorker uses shared context."""
        from camel.utils.context_utils import ContextUtility

        # Reset any existing shared sessions
        ContextUtility.reset_shared_sessions()

        worker = MockSingleAgentWorker("test_worker")

        # Get context utility - should use shared instance
        context_util = worker._get_context_utility()

        # Should be the same as calling get_workforce_shared
        shared_context = ContextUtility.get_workforce_shared()
        assert context_util is shared_context


class TestSmartWorkflowSelection:
    """Test smart workflow selection feature."""

    def test_smart_selection_with_metadata(self, temp_context_dir):
        """Test smart workflow selection using metadata."""
        worker = MockSingleAgentWorker("data_analyst")

        # Mock workflow metadata
        mock_metadata = [
            {
                'title': 'Data Analysis Workflow',
                'description': 'Analyze sales data and generate reports',
                'tags': ['data-analysis', 'statistics', 'reporting'],
                'file_path': (
                    f"{temp_context_dir}/session_1/data_analyst_workflow.md"
                ),
            },
            {
                'title': 'Web Scraping Workflow',
                'description': 'Scrape website data',
                'tags': ['web-scraping', 'data-collection'],
                'file_path': (
                    f"{temp_context_dir}/session_1/web_scraper_workflow.md"
                ),
            },
            {
                'title': 'Database Query Workflow',
                'description': 'Query database for analysis',
                'tags': ['database', 'sql', 'data-analysis'],
                'file_path': (
                    f"{temp_context_dir}/session_1/db_analyst_workflow.md"
                ),
            },
        ]

        # Mock context utility to return metadata
        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_metadata.return_value = (
            mock_metadata
        )
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        # Mock agent response to select first workflow
        mock_agent_response = MagicMock()
        mock_agent_response.msgs = [MagicMock(content="1, 3")]

        # Mock get_workforce_shared to return our mock context utility
        with (
            patch(
                'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
                return_value=mock_context_utility,
            ),
            patch.object(
                worker.worker, 'step', return_value=mock_agent_response
            ),
        ):
            result = worker.load_workflow_memories(
                max_workflows=2, use_smart_selection=True
            )

            # Verify smart selection was used
            assert result is True
            mock_context_utility.get_all_workflows_metadata.assert_called_once()
            worker.worker.step.assert_called_once()

            # Verify agent was asked to select workflows
            selection_call = worker.worker.step.call_args[0][0]
            assert "data_analyst" in selection_call.content
            assert "select the 2 most relevant" in selection_call.content
            assert "data-analysis" in selection_call.content

    def test_smart_selection_no_metadata(self, temp_context_dir):
        """Test smart selection when no workflow metadata found."""
        worker = MockSingleAgentWorker("data_analyst")

        # Mock context utility to return empty metadata
        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_metadata.return_value = []

        with patch(
            'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            result = worker.load_workflow_memories(use_smart_selection=True)

            assert result is False
            mock_context_utility.get_all_workflows_metadata.assert_called_once()

    def test_smart_selection_fewer_workflows_than_max(self, temp_context_dir):
        """Test smart selection when fewer workflows exist than max_files."""
        worker = MockSingleAgentWorker("data_analyst")

        # Mock only 2 workflows but ask for 5
        mock_metadata = [
            {
                'title': 'Workflow 1',
                'description': 'Test workflow 1',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_1/workflow1.md",
            },
            {
                'title': 'Workflow 2',
                'description': 'Test workflow 2',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_1/workflow2.md",
            },
        ]

        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_metadata.return_value = (
            mock_metadata
        )
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        with patch(
            'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            result = worker.load_workflow_memories(
                max_workflows=5, use_smart_selection=True
            )

            # Should load all 2 workflows without agent selection
            assert result is True
            assert mock_context_utility.load_markdown_file.call_count == 2

    def test_smart_selection_agent_selection_failure_fallback(
        self, temp_context_dir
    ):
        """Test fallback to most recent when agent selection fails."""
        worker = MockSingleAgentWorker("data_analyst")

        mock_metadata = [
            {
                'title': 'Workflow 1',
                'description': 'Test',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_1/workflow1.md",
            },
            {
                'title': 'Workflow 2',
                'description': 'Test',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_1/workflow2.md",
            },
            {
                'title': 'Workflow 3',
                'description': 'Test',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_1/workflow3.md",
            },
        ]

        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_metadata.return_value = (
            mock_metadata
        )
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        # Mock agent to return invalid response
        mock_agent_response = MagicMock()
        mock_agent_response.msgs = [MagicMock(content="invalid response")]

        with (
            patch(
                'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
                return_value=mock_context_utility,
            ),
            patch.object(
                worker.worker, 'step', return_value=mock_agent_response
            ),
        ):
            result = worker.load_workflow_memories(
                max_workflows=2, use_smart_selection=True
            )

            # Should fallback to first 2 workflows (most recent)
            assert result is True
            assert mock_context_utility.load_markdown_file.call_count == 2

    def test_smart_selection_memory_cleanup(self, temp_context_dir):
        """Test that agent memory is cleaned after smart selection."""
        worker = MockSingleAgentWorker("data_analyst")

        mock_metadata = [
            {
                'title': 'Test Workflow',
                'description': 'Test',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_1/workflow.md",
            }
        ]

        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_metadata.return_value = (
            mock_metadata
        )
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        with patch(
            'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            result = worker.load_workflow_memories(use_smart_selection=True)

            assert result is True

            # Memory should be cleaned (only system message remains)
            final_memory = worker.worker.memory.get_context()[0]
            # Should have system message only
            assert len(final_memory) == 1

    def test_extract_workflow_metadata(self, temp_context_dir):
        """Test metadata extraction from workflow markdown file."""
        from camel.utils.context_utils import ContextUtility

        # Create a test workflow file
        workflow_content = """### Task Title
Data Analysis Workflow

### Task Description
Analyze sales data and generate comprehensive reports with visualizations.

### Tags
- data-analysis
- statistics
- reporting
- visualization

### Steps Taken
1. Load data
2. Clean data
3. Analyze trends
"""
        workflow_path = f"{temp_context_dir}/test_workflow.md"
        with open(workflow_path, 'w') as f:
            f.write(workflow_content)

        # Extract metadata
        context_util = ContextUtility.get_workforce_shared()
        metadata = context_util.extract_workflow_metadata(workflow_path)

        assert metadata['title'] == "Data Analysis Workflow"
        assert "sales data" in metadata['description']
        assert 'data-analysis' in metadata['tags']
        assert 'statistics' in metadata['tags']
        assert 'reporting' in metadata['tags']
        assert 'visualization' in metadata['tags']
        assert metadata['file_path'] == workflow_path

    def test_get_all_workflows_metadata(self, temp_context_dir):
        """Test getting metadata from all workflow files."""
        # Create test workflow files
        import os

        from camel.utils.context_utils import ContextUtility

        os.makedirs(
            f"{temp_context_dir}/workforce_workflows/session_1", exist_ok=True
        )
        os.makedirs(
            f"{temp_context_dir}/workforce_workflows/session_2", exist_ok=True
        )

        workflow1 = (
            f"{temp_context_dir}/workforce_workflows/session_1/"
            "analyst_workflow.md"
        )
        workflow2 = (
            f"{temp_context_dir}/workforce_workflows/session_2/"
            "developer_workflow.md"
        )

        with open(workflow1, 'w') as f:
            f.write("""### Task Title
Analysis Workflow

### Task Description
Data analysis

### Tags
- data-analysis
""")

        with open(workflow2, 'w') as f:
            f.write("""### Task Title
Development Workflow

### Task Description
Code development

### Tags
- development
- coding
""")

        # Get all metadata
        context_util = ContextUtility.get_workforce_shared()
        all_metadata = context_util.get_all_workflows_metadata()

        assert len(all_metadata) == 2
        titles = [m['title'] for m in all_metadata]
        assert "Analysis Workflow" in titles
        assert "Development Workflow" in titles

    def test_smart_selection_with_session_filter(self, temp_context_dir):
        """Test smart selection with specific session ID."""
        worker = MockSingleAgentWorker("data_analyst")

        mock_metadata = [
            {
                'title': 'Test Workflow',
                'description': 'Test',
                'tags': ['test'],
                'file_path': f"{temp_context_dir}/session_123/workflow.md",
            }
        ]

        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_metadata.return_value = (
            mock_metadata
        )
        mock_context_utility.load_markdown_file.return_value = (
            "# Workflow content\nThis is workflow data"
        )
        mock_context_utility._filter_metadata_from_content.return_value = (
            "This is workflow data"
        )

        with patch(
            'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            result = worker.load_workflow_memories(
                session_id="session_123", use_smart_selection=True
            )

            assert result is True
            # Verify session_id was passed to get_all_workflows_metadata
            mock_context_utility.get_all_workflows_metadata.assert_called_once_with(
                "session_123"
            )

    def test_practical_smart_selection(self, temp_context_dir):
        """Test smart selection with 10 real workflow files in temp
        directory.
        """
        import os

        # Create session directory in workforce_workflows
        session_dir = os.path.join(
            temp_context_dir, "workforce_workflows", "session_test"
        )
        os.makedirs(session_dir, exist_ok=True)

        # Create 10 different workflow files with varied content
        workflows = [
            {
                "name": "data_analysis_workflow.md",
                "title": "Data Analysis Pipeline",
                "description": (
                    "Analyze CSV data and generate statistical reports"
                ),
                "tags": ["data-analysis", "statistics", "csv-processing"],
            },
            {
                "name": "web_scraping_workflow.md",
                "title": "Web Scraper",
                "description": "Scrape product data from e-commerce websites",
                "tags": ["web-scraping", "data-collection", "api-integration"],
            },
            {
                "name": "email_automation_workflow.md",
                "title": "Email Campaign Manager",
                "description": "Send automated marketing emails to customers",
                "tags": ["email-automation", "marketing", "communication"],
            },
            {
                "name": "image_processing_workflow.md",
                "title": "Image Optimizer",
                "description": "Resize and compress images for web use",
                "tags": [
                    "image-processing",
                    "file-processing",
                    "optimization",
                ],
            },
            {
                "name": "database_query_workflow.md",
                "title": "Database Reporter",
                "description": "Query database and generate business reports",
                "tags": ["database-query", "sql", "report-generation"],
            },
            {
                "name": "api_integration_workflow.md",
                "title": "API Connector",
                "description": "Connect to external APIs and sync data",
                "tags": ["api-integration", "data-sync", "web-services"],
            },
            {
                "name": "text_processing_workflow.md",
                "title": "Text Analyzer",
                "description": "Process and analyze large text documents",
                "tags": ["text-processing", "nlp", "data-analysis"],
            },
            {
                "name": "code_generation_workflow.md",
                "title": "Code Generator",
                "description": "Generate boilerplate code from templates",
                "tags": ["code-generation", "automation", "development"],
            },
            {
                "name": "file_organizer_workflow.md",
                "title": "File Organizer",
                "description": "Organize files by type and date",
                "tags": ["file-processing", "automation", "organization"],
            },
            {
                "name": "report_builder_workflow.md",
                "title": "Report Builder",
                "description": "Build PDF reports from data sources",
                "tags": ["report-generation", "pdf", "data-visualization"],
            },
        ]

        # Write workflow files
        for workflow in workflows:
            file_path = os.path.join(session_dir, workflow["name"])
            content = f"""## Metadata

- session_id: session_test
- working_directory: {session_dir}
- created_at: 2025-01-15T10:00:00.000000
- agent_id: test-agent-id
- message_count: 5

## WorkflowSummary

### Task Title
{workflow["title"]}

### Task Description
{workflow["description"]}

### Tags
{", ".join(workflow["tags"])}

### Tools
(No tools recorded)

### Steps
1. Initial step
2. Processing step
3. Final step

### Failure And Recovery Strategies
(No failure and recovery strategies recorded)

### Notes And Observations
(No notes and observations provided)
"""
            with open(file_path, 'w') as f:
                f.write(content)

        # Create worker that needs data analysis
        worker = MockSingleAgentWorker("data_analyst")

        # Mock the agent to select data-related workflows
        mock_agent_response = MagicMock()
        mock_agent_response.msgs = [
            MagicMock(
                content="Based on the role, I select: 1, 5, 7"
            )  # data_analysis, database_query, text_processing
        ]

        # Create real ContextUtility to test actual metadata extraction
        from pathlib import Path

        from camel.utils.context_utils import ContextUtility

        # Save the original function before patching
        original_get_workforce_shared = ContextUtility.get_workforce_shared

        # Create a side_effect function that returns properly
        # configured utilities
        def get_utility_with_base_dir(session_id=None):
            utility = original_get_workforce_shared(session_id)
            utility._base_directory = Path(temp_context_dir)
            return utility

        # Store original system message before loading
        original_system_message = worker.worker._system_message.content

        with (
            patch(
                'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
                side_effect=get_utility_with_base_dir,
            ),
            patch.object(
                worker.worker, 'step', return_value=mock_agent_response
            ),
        ):
            # Load with smart selection (max 3 files)
            result = worker.load_workflow_memories(
                max_workflows=3, use_smart_selection=True
            )

            # Verify success
            assert result is True

            # Verify agent was asked to select
            assert worker.worker.step.called

            # Verify that workflows were actually added to the system message
            updated_system_message = worker.worker._system_message.content

            # System message should be different from original
            # (workflows added)
            assert updated_system_message != original_system_message

            # System message should contain workflow titles from the
            # loaded files. At least some workflow-related content
            # should be present
            assert len(updated_system_message) > len(original_system_message)

            # Verify system message contains workflow metadata
            assert "Previous Workflows" in updated_system_message
