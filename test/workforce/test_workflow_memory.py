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
            result = worker.save_workflow()

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

        result = worker.save_workflow()

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
            result = worker.save_workflow()

            assert result["status"] == "error"
            assert "Failed to save workflow: Test error" in result["message"]

    @patch('glob.glob')
    @patch('os.path.getmtime')
    def test_load_workflow_success(
        self, mock_getmtime, mock_glob, temp_context_dir
    ):
        """Test successful workflow loading."""
        worker = MockSingleAgentWorker("data_analyst")

        # Mock file discovery
        mock_files = [
            f"{temp_context_dir}/session_123/"
            "data_analyst_workflow_20250122.md"
        ]
        mock_glob.return_value = mock_files
        mock_getmtime.return_value = 1234567890

        # Mock the shared context utility method
        mock_context_utility = MagicMock()
        mock_context_utility.load_markdown_context_to_memory.return_value = (
            "Context appended successfully"
        )

        with patch(
            'camel.utils.context_utils.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            result = worker.load_workflow()

            assert result is True
            mock_context_utility.load_markdown_context_to_memory.assert_called()

    def test_load_workflow_no_files(self, temp_context_dir):
        """Test workflow loading when no files found."""
        worker = MockSingleAgentWorker("data_analyst")

        with patch('glob.glob', return_value=[]):
            result = worker.load_workflow()

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

        result = worker.load_workflow()

        assert result is False


class TestWorkforceWorkflowMethods:
    """Test workflow functionality for Workforce."""

    def test_save_workflows_success(self, mock_workforce):
        """Test successful workflow saving for all workers."""
        # Mock save_workflow for both workers
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
                'save_workflow',
                return_value=mock_result_1,
            ),
            patch.object(
                mock_workforce._children[1],
                'save_workflow',
                return_value=mock_result_2,
            ),
        ):
            results = mock_workforce.save_workflows()

            assert len(results) == 2
            assert all("/path/to/" in path for path in results.values())

    def test_save_workflows_mixed_results(self, mock_workforce):
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
                'save_workflow',
                return_value=mock_result_success,
            ),
            patch.object(
                mock_workforce._children[1],
                'save_workflow',
                return_value=mock_result_error,
            ),
        ):
            results = mock_workforce.save_workflows()

            assert len(results) == 2
            assert (
                "/path/to/data_analyst_workflow.md"
                in results[mock_workforce._children[0].node_id]
            )
            assert (
                "error: No conversation context"
                in results[mock_workforce._children[1].node_id]
            )

    def test_save_workflows_exception(self, mock_workforce):
        """Test workflow saving when exception occurs."""
        with patch.object(
            mock_workforce._children[0],
            'save_workflow',
            side_effect=Exception("Test error"),
        ):
            results = mock_workforce.save_workflows()

            assert (
                "error: Test error"
                in results[mock_workforce._children[0].node_id]
            )

    def test_load_workflows_success(self, mock_workforce):
        """Test successful workflow loading for all workers."""
        with (
            patch.object(
                mock_workforce._children[0], 'load_workflow', return_value=True
            ),
            patch.object(
                mock_workforce._children[1], 'load_workflow', return_value=True
            ),
        ):
            results = mock_workforce.load_workflows()

            assert len(results) == 2
            assert all(success for success in results.values())

    def test_load_workflows_mixed_results(self, mock_workforce):
        """Test workflow loading with mixed success/failure results."""
        with (
            patch.object(
                mock_workforce._children[0], 'load_workflow', return_value=True
            ),
            patch.object(
                mock_workforce._children[1],
                'load_workflow',
                return_value=False,
            ),
        ):
            results = mock_workforce.load_workflows()

            assert results[mock_workforce._children[0].node_id] is True
            assert results[mock_workforce._children[1].node_id] is False

    def test_load_workflows_exception(self, mock_workforce):
        """Test workflow loading when exception occurs."""
        with patch.object(
            mock_workforce._children[0],
            'load_workflow',
            side_effect=Exception("Test error"),
        ):
            results = mock_workforce.load_workflows()

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
        save_results = workforce.save_workflows()
        assert (
            "skipped: MagicMock not supported"
            in save_results[mock_role_playing_worker.node_id]
        )

        # Test load_workflows
        load_results = workforce.load_workflows()
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
            save_results = workforce1.save_workflows()
            assert (
                save_results[worker1.node_id] == mock_save_result["file_path"]
            )

        # Second session: create new workforce and load workflows
        workforce2 = Workforce("Test Team")
        worker2 = MockSingleAgentWorker("data_analyst")
        workforce2._children = [worker2]

        # Mock successful workflow loading
        with patch.object(worker2, 'load_workflow', return_value=True):
            load_results = workforce2.load_workflows()
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
                result = worker.save_workflow()
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
