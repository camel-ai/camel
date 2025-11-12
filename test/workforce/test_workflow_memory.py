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


@pytest.fixture(autouse=True)
def mock_model_backend():
    """Use StubModel to prevent real LLM API calls in tests."""
    from camel.models.stub_model import StubModel
    from camel.types import ModelType

    # Use the existing StubModel designed for unit tests
    stub_model = StubModel(model_type=ModelType.STUB)

    with patch('camel.models.ModelFactory.create', return_value=stub_model):
        yield stub_model


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

    @pytest.mark.asyncio
    async def test_save_workflow_success(self, temp_context_dir):
        """Test successful workflow saving."""
        worker = MockSingleAgentWorker("test_analyst")

        # Mock the asummarize method to return success
        mock_result = {
            "status": "success",
            "summary": "Test workflow summary",
            "file_path": (
                f"{temp_context_dir}/test_analyst_workflow_20250122.md"
            ),
        }

        with patch.object(
            worker.worker, 'asummarize', return_value=mock_result
        ):
            result = await worker.save_workflow_memories_async()

            assert result["status"] == "success"
            assert result["worker_description"] == "test_analyst"
            assert "test_analyst_workflow_" in result["file_path"]

    @pytest.mark.asyncio
    async def test_save_workflow_non_chat_agent(self):
        """Test workflow saving with non-ChatAgent worker."""
        # Create worker and then replace worker with non-ChatAgent
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="Test"
        )
        worker = SingleAgentWorker("test", ChatAgent(sys_msg))

        # Replace the worker with a non-ChatAgent object
        worker.worker = "not_a_chat_agent"

        # With the refactored code, TypeError is raised during
        # WorkflowMemoryManager initialization
        with pytest.raises(TypeError, match="Worker must be a ChatAgent"):
            await worker.save_workflow_memories_async()

    @pytest.mark.asyncio
    async def test_save_workflow_exception(self, temp_context_dir):
        """Test workflow saving when exception occurs."""
        worker = MockSingleAgentWorker("test_analyst")

        # Mock asummarize to raise exception
        with patch.object(
            worker.worker, 'asummarize', side_effect=Exception("Test error")
        ):
            result = await worker.save_workflow_memories_async()

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

        # With the refactored code, TypeError is raised during
        # WorkflowMemoryManager initialization
        with pytest.raises(TypeError, match="Worker must be a ChatAgent"):
            worker.load_workflow_memories()

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

    @pytest.mark.asyncio
    async def test_save_workflow_memories_success(self, mock_workforce):
        """Test successful workflow saving for all workers."""
        # Mock save_workflow_memories_async for both workers
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
                'save_workflow_memories_async',
                return_value=mock_result_1,
            ),
            patch.object(
                mock_workforce._children[1],
                'save_workflow_memories_async',
                return_value=mock_result_2,
            ),
        ):
            results = await mock_workforce.save_workflow_memories_async()

            assert len(results) == 2
            assert all("/path/to/" in path for path in results.values())

    @pytest.mark.asyncio
    async def test_save_workflow_memories_mixed_results(self, mock_workforce):
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
                'save_workflow_memories_async',
                return_value=mock_result_success,
            ),
            patch.object(
                mock_workforce._children[1],
                'save_workflow_memories_async',
                return_value=mock_result_error,
            ),
        ):
            results = await mock_workforce.save_workflow_memories_async()

            assert len(results) == 2
            assert (
                "/path/to/data_analyst_workflow.md"
                in results[mock_workforce._children[0].node_id]
            )
            assert (
                "error: No conversation context"
                in results[mock_workforce._children[1].node_id]
            )

    @pytest.mark.asyncio
    async def test_save_workflow_memories_exception(self, mock_workforce):
        """Test workflow saving when exception occurs."""
        with patch.object(
            mock_workforce._children[0],
            'save_workflow_memories_async',
            side_effect=Exception("Test error"),
        ):
            results = await mock_workforce.save_workflow_memories_async()

            assert (
                "error: Test error"
                in results[mock_workforce._children[0].node_id]
            )

    @pytest.mark.asyncio
    async def test_save_workflow_memories_real_execution(
        self, temp_context_dir
    ):
        """Test save_workflow_memories_async with real internal execution.

        This test exercises the actual save_workflow_memories_async()
        implementation, only mocking the ChatAgent.asummarize() method to
        avoid LLM API calls.

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

        # Mock only the ChatAgent.asummarize() method (which makes LLM calls)
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
            ChatAgent, 'asummarize', return_value=mock_summary_result
        ) as mock_asummarize:
            # This executes the real save_workflow_memories_async() logic
            results = await workforce.save_workflow_memories_async()

            # Verify Workforce correctly processes worker results
            assert len(results) == 1
            assert worker.node_id in results
            assert "data_analyst_workflow" in results[worker.node_id]
            assert results[worker.node_id] == mock_summary_result["file_path"]

            # Verify shared context utility was set up correctly
            assert worker.worker._context_utility is not None

            # Verify ChatAgent.asummarize was called with correct parameters
            # (validates filename generation, prompt preparation, agent
            # selection)
            mock_asummarize.assert_called_once()
            call_kwargs = mock_asummarize.call_args[1]

            # Verify filename generation includes worker role_name
            # (not description, as that would be too long)
            assert 'filename' in call_kwargs
            # MockSingleAgentWorker uses "Test Worker" as role_name
            assert 'test_worker_workflow' in call_kwargs['filename']

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

    @pytest.mark.asyncio
    async def test_workflows_skip_non_single_agent_workers(self):
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
        save_results = await workforce.save_workflow_memories_async()
        assert (
            "skipped: MagicMock not supported"
            in save_results[mock_role_playing_worker.node_id]
        )

        # Test load_workflows
        load_results = workforce.load_workflow_memories()
        assert load_results[mock_role_playing_worker.node_id] is False


class TestWorkflowIntegration:
    """Integration tests for workflow functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_memory(self, temp_context_dir):
        """Test complete workflow: save workflow, load in new session."""
        # First session: create workforce and mock workflow saving
        workforce1 = Workforce("Test Team")
        worker1 = MockSingleAgentWorker("data_analyst")
        workforce1._children = [worker1]

        # Mock successful asummarize and save
        mock_save_result = {
            "status": "success",
            "summary": "Data analysis workflow completed",
            "file_path": f"{temp_context_dir}/data_analyst_workflow_test.md",
        }

        with patch.object(
            worker1.worker, 'asummarize', return_value=mock_save_result
        ):
            save_results = await workforce1.save_workflow_memories_async()
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

    @pytest.mark.asyncio
    async def test_filename_sanitization(self):
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
                worker.worker, 'asummarize', return_value=mock_result
            ):
                # Verify the filename generation works with special characters
                result = await worker.save_workflow_memories_async()
                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_long_description_filename_generation(
        self, temp_context_dir
    ):
        """Test that very long descriptions don't create unwieldy filenames.

        This test addresses issue #3277 where long worker descriptions
        caused filesystem errors due to excessive filename lengths.
        """
        # create worker with extremely long description (like in eigent.py)
        long_desc = (
            "Developer Agent: A master-level coding assistant with a "
            "powerful terminal. It can write and execute code, manage "
            "files, automate desktop tasks, and deploy web applications "
            "to solve complex technical challenges."
        )

        # create a test worker with long description but short role_name
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content="You are a developer agent.",
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description=long_desc,
            worker=agent,
            enable_workflow_memory=True,
        )

        # mock the asummarize method
        mock_result = {
            "status": "success",
            "summary": "Test workflow summary",
            "file_path": f"{temp_context_dir}/developer_agent_workflow.md",
        }

        with patch.object(agent, 'asummarize', return_value=mock_result):
            result = await worker.save_workflow_memories_async()

            assert result["status"] == "success"

            # verify filename is reasonable length (< 100 chars including path)
            filename = os.path.basename(result["file_path"])
            assert (
                len(filename) < 100
            ), f"Filename too long: {len(filename)} chars - {filename}"

            # verify filename uses role_name, not full description
            assert "developer_agent_workflow" in filename
            assert "master_level_coding_assistant" not in filename

    @pytest.mark.asyncio
    async def test_filename_generation_with_generic_role_name(
        self, temp_context_dir
    ):
        """Test filename generation with generic role_name uses task_title.

        When agent has a generic role_name like "assistant", the filename
        should be based on the task_title from the generated workflow summary.
        """
        # create worker with generic role_name
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Assistant",  # generic role name
            content="You are a helpful assistant.",
        )
        agent = ChatAgent(sys_msg)

        worker = SingleAgentWorker(
            description="Data analyst worker",
            worker=agent,
            enable_workflow_memory=True,
        )

        # verify role_name is generic
        assert agent.role_name.lower() in {
            'assistant',
            'agent',
            'user',
            'system',
        }

        # mock the asummarize method to return a workflow with task_title
        mock_result = {
            "status": "success",
            "summary": "Test workflow summary",
            "file_path": f"{temp_context_dir}/analyze_sales_data_workflow.md",
            "structured_summary": type(
                'obj', (object,), {'task_title': 'Analyze sales data'}
            )(),
        }

        with patch.object(agent, 'asummarize', return_value=mock_result):
            # note: in real execution, file would be renamed to use task_title
            # the test shows that with generic role_name, we rely on task_title
            result = await worker.save_workflow_memories_async()

            assert result["status"] == "success"
            # filename should be based on task_title, not role_name
            assert (
                "sales" in result["file_path"]
                or "analyze" in result["file_path"]
            )

    @pytest.mark.asyncio
    async def test_custom_session_id_integration(self, temp_context_dir):
        """Test end-to-end workflow with custom session ID.

        This test addresses issue #3277 request for custom session IDs.
        """
        # create workforce with custom session id
        workforce = Workforce("Test Team")
        worker = MockSingleAgentWorker("test_analyst")
        workforce._children = [worker]

        custom_session = "project_abc123"

        # simulate conversation
        user_msg = BaseMessage.make_user_message(
            role_name="User", content="Analyze data"
        )
        assistant_msg = BaseMessage.make_assistant_message(
            role_name="Assistant", content="Analysis complete"
        )
        worker.worker.record_message(user_msg)
        worker.worker.record_message(assistant_msg)

        # mock the asummarize method
        expected_path = (
            f"{temp_context_dir}/workforce_workflows/"
            f"{custom_session}/test_worker_workflow.md"
        )
        mock_result = {
            "status": "success",
            "summary": "Test workflow",
            "file_path": expected_path,
        }

        with patch.object(ChatAgent, 'asummarize', return_value=mock_result):
            # save with custom session id
            results = await workforce.save_workflow_memories_async(
                session_id=custom_session
            )

            # verify results contain the custom session path
            assert worker.node_id in results
            assert custom_session in results[worker.node_id]

            # verify the shared context utility was created with custom
            # session
            assert workforce._shared_context_utility is not None
            assert (
                workforce._shared_context_utility.session_id == custom_session
            )


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

        # Mock context utility to return info
        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_info.return_value = (
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
            mock_context_utility.get_all_workflows_info.assert_called_once()
            worker.worker.step.assert_called_once()

            # Verify agent was asked to select workflows
            selection_call = worker.worker.step.call_args[0][0]
            assert "data_analyst" in selection_call.content
            assert "select the 2 most relevant" in selection_call.content
            assert "data-analysis" in selection_call.content

    def test_smart_selection_no_metadata(self, temp_context_dir):
        """Test smart selection when no workflow info found."""
        worker = MockSingleAgentWorker("data_analyst")

        # Mock context utility to return empty info
        mock_context_utility = MagicMock()
        mock_context_utility.get_all_workflows_info.return_value = []

        with patch(
            'camel.societies.workforce.workflow_memory_manager.ContextUtility.get_workforce_shared',
            return_value=mock_context_utility,
        ):
            result = worker.load_workflow_memories(use_smart_selection=True)

            assert result is False
            mock_context_utility.get_all_workflows_info.assert_called_once()

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
        mock_context_utility.get_all_workflows_info.return_value = (
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
        mock_context_utility.get_all_workflows_info.return_value = (
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
        mock_context_utility.get_all_workflows_info.return_value = (
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

    def test_extract_workflow_info(self, temp_context_dir):
        """Test info extraction from workflow markdown file."""
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

        # Extract info
        context_util = ContextUtility.get_workforce_shared()
        metadata = context_util.extract_workflow_info(workflow_path)

        assert metadata['title'] == "Data Analysis Workflow"
        assert "sales data" in metadata['description']
        assert 'data-analysis' in metadata['tags']
        assert 'statistics' in metadata['tags']
        assert 'reporting' in metadata['tags']
        assert 'visualization' in metadata['tags']
        assert metadata['file_path'] == workflow_path

    def test_get_all_workflows_info(self, temp_context_dir):
        """Test getting info from all workflow files."""
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

        # Get all info
        context_util = ContextUtility.get_workforce_shared()
        all_metadata = context_util.get_all_workflows_info()

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
        mock_context_utility.get_all_workflows_info.return_value = (
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
            # Verify session_id was passed to get_all_workflows_info
            mock_context_utility.get_all_workflows_info.assert_called_once_with(
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


class TestWorkforceMemorySharing:
    """Test Workforce memory sharing and deduplication."""

    def test_share_memory_deduplication(self):
        """Test that Workforce prevents duplicate records from being re-shared.

        This test verifies that the Workforce layer deduplicates records based
        on UUID to prevent exponential growth of duplicate records across
        agents.
        """
        import uuid

        from camel.memories.records import MemoryRecord
        from camel.messages import BaseMessage

        # Create a workforce with share_memory enabled
        workforce = Workforce("Test Workforce", share_memory=True)

        # Create mock workers
        worker1 = MockSingleAgentWorker("worker_1")
        worker2 = MockSingleAgentWorker("worker_2")
        workforce._children = [worker1, worker2]

        # Initialize workforce agents (needed for memory operations)
        from camel.agents import ChatAgent

        sys_msg = BaseMessage.make_assistant_message(
            role_name="Coordinator", content="Test coordinator"
        )
        workforce.coordinator_agent = ChatAgent(sys_msg)
        workforce.task_agent = ChatAgent(sys_msg)

        # Create test records with UUIDs
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        uuid3 = str(uuid.uuid4())

        msg1 = BaseMessage.make_user_message(
            role_name="user", content="Message 1"
        )
        msg2 = BaseMessage.make_user_message(
            role_name="user", content="Message 2"
        )
        msg3 = BaseMessage.make_user_message(
            role_name="user", content="Message 3"
        )

        record1 = MemoryRecord(
            message=msg1, role_at_backend="user", uuid=uuid1
        )
        record1.agent_id = "worker_1"

        record2 = MemoryRecord(
            message=msg2, role_at_backend="user", uuid=uuid2
        )
        record2.agent_id = "worker_1"

        record3 = MemoryRecord(
            message=msg3, role_at_backend="user", uuid=uuid3
        )
        record3.agent_id = "worker_2"

        # Simulate first sync cycle - 3 new records
        shared_memory_cycle1 = {
            'coordinator': [],
            'task_agent': [],
            'workers': [
                record1.to_dict(),
                record2.to_dict(),
                record3.to_dict(),
            ],
        }

        workforce._share_memory_with_agents(shared_memory_cycle1)

        # Verify tracking: all 3 UUIDs should be tracked
        assert len(workforce._shared_memory_uuids) == 3
        assert uuid1 in workforce._shared_memory_uuids
        assert uuid2 in workforce._shared_memory_uuids
        assert uuid3 in workforce._shared_memory_uuids

        # Simulate second sync cycle - same records collected again (circular
        # sharing)
        shared_memory_cycle2 = {
            'coordinator': [
                record1.to_dict(),
                record2.to_dict(),
                record3.to_dict(),
            ],
            'task_agent': [
                record1.to_dict(),
                record2.to_dict(),
                record3.to_dict(),
            ],
            'workers': [
                record1.to_dict(),
                record2.to_dict(),
                record3.to_dict(),
            ],
        }

        # Count coordinator memory before second sync
        coord_memory_before = len(
            workforce.coordinator_agent.memory.retrieve()
        )

        workforce._share_memory_with_agents(shared_memory_cycle2)

        # Verify no duplicates were shared (all filtered out)
        coord_memory_after = len(workforce.coordinator_agent.memory.retrieve())
        assert (
            coord_memory_after == coord_memory_before
        )  # No new records added

        # Verify UUID tracking didn't grow (still only 3 unique UUIDs)
        assert len(workforce._shared_memory_uuids) == 3

    def test_share_memory_mixed_new_and_duplicate(self):
        """Test memory sharing with a mix of new and already-shared records."""
        import uuid

        from camel.memories.records import MemoryRecord
        from camel.messages import BaseMessage

        # Create workforce with share_memory enabled
        workforce = Workforce("Test Workforce", share_memory=True)
        worker = MockSingleAgentWorker("worker_1")
        workforce._children = [worker]

        # Initialize workforce agents
        from camel.agents import ChatAgent

        sys_msg = BaseMessage.make_assistant_message(
            role_name="Coordinator", content="Test coordinator"
        )
        workforce.coordinator_agent = ChatAgent(sys_msg)
        workforce.task_agent = ChatAgent(sys_msg)

        # First sync: 2 records
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        msg1 = BaseMessage.make_user_message(
            role_name="user", content="Message 1"
        )
        msg2 = BaseMessage.make_user_message(
            role_name="user", content="Message 2"
        )

        record1 = MemoryRecord(
            message=msg1, role_at_backend="user", uuid=uuid1
        )
        record1.agent_id = "worker_1"
        record2 = MemoryRecord(
            message=msg2, role_at_backend="user", uuid=uuid2
        )
        record2.agent_id = "worker_1"

        shared_memory1 = {
            'coordinator': [],
            'task_agent': [],
            'workers': [record1.to_dict(), record2.to_dict()],
        }
        workforce._share_memory_with_agents(shared_memory1)

        assert len(workforce._shared_memory_uuids) == 2

        # Second sync: Mix of old (uuid1, uuid2) and new (uuid3)
        uuid3 = str(uuid.uuid4())
        msg3 = BaseMessage.make_user_message(
            role_name="user", content="Message 3"
        )
        record3 = MemoryRecord(
            message=msg3, role_at_backend="user", uuid=uuid3
        )
        record3.agent_id = "worker_1"

        coord_memory_before = len(
            workforce.coordinator_agent.memory.retrieve()
        )

        shared_memory2 = {
            'coordinator': [],
            'task_agent': [],
            'workers': [
                record1.to_dict(),  # Duplicate
                record2.to_dict(),  # Duplicate
                record3.to_dict(),  # NEW!
            ],
        }
        workforce._share_memory_with_agents(shared_memory2)

        # Verify only the new record was shared (uuid3)
        assert len(workforce._shared_memory_uuids) == 3
        assert uuid3 in workforce._shared_memory_uuids

        # Coordinator should only receive 1 new record (not all 3)
        coord_memory_after = len(workforce.coordinator_agent.memory.retrieve())
        assert coord_memory_after == coord_memory_before + 1


class TestConversationAccumulator:
    """Test conversation accumulator behavior - critical for workflow
    memory.
    """

    @pytest.mark.asyncio
    async def test_accumulator_collects_from_multiple_tasks(
        self, temp_context_dir
    ):
        """Test that accumulator properly collects conversations from
        multiple task executions.

        This validates the core accumulation mechanism across multiple
        tasks, ensuring all conversations are captured before
        summarization.
        """
        # create worker with workflow memory enabled
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=agent,
            enable_workflow_memory=True,
            use_agent_pool=False,  # disable pooling for simpler test
        )

        # process multiple tasks
        task1 = Task(content="Calculate 2+2", id="t1")
        task2 = Task(content="Analyze data trends", id="t2")
        task3 = Task(content="Generate summary report", id="t3")

        # mock the step method to simulate task processing
        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Task completed"
            )

            await worker._process_task(task1, [])
            await worker._process_task(task2, [])
            await worker._process_task(task3, [])

        # verify accumulator was created
        assert (
            worker._conversation_accumulator is not None
        ), "Accumulator should be created when workflow memory is enabled"

        # verify accumulator has messages from ALL tasks
        accumulator = worker._conversation_accumulator
        records = accumulator.memory.retrieve()

        # should contain messages from all 3 tasks
        # each task creates user message + assistant response
        assert len(records) >= 6, (
            f"Expected at least 6 messages (3 tasks * 2 messages each), "
            f"got {len(records)}"
        )

        # verify messages are about the tasks we created
        messages_content = [
            record.memory_record.message.content for record in records
        ]
        assert any(
            "2+2" in content for content in messages_content
        ), "Should contain content from task1"
        assert any(
            "data trends" in content for content in messages_content
        ), "Should contain content from task2"
        assert any(
            "summary report" in content for content in messages_content
        ), "Should contain content from task3"

    @pytest.mark.asyncio
    async def test_workflow_memory_disabled_skips_accumulation(
        self, temp_context_dir
    ):
        """Test that enable_workflow_memory=False prevents accumulation.

        Verifies the feature can be disabled and doesn't impact performance
        with unnecessary memory operations.
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=agent,
            enable_workflow_memory=False,  # explicitly disabled
            use_agent_pool=False,
        )

        # process a task
        task = Task(content="Process this task", id="t1")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Task completed"
            )
            await worker._process_task(task, [])

        # accumulator should NOT be created when disabled
        assert worker._conversation_accumulator is None, (
            "Accumulator should not be created when "
            "enable_workflow_memory=False"
        )

    @pytest.mark.asyncio
    async def test_accumulator_cleanup_after_successful_save(
        self, temp_context_dir
    ):
        """Test that accumulator is cleared after successful workflow save.

        Validates cleanup to prevent memory leaks and duplicate content
        in future saves.
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=agent,
            enable_workflow_memory=True,
            use_agent_pool=False,
        )

        # process tasks to create accumulator
        task1 = Task(content="Task 1", id="t1")
        task2 = Task(content="Task 2", id="t2")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Done"
            )
            await worker._process_task(task1, [])
            await worker._process_task(task2, [])

        # verify accumulator exists
        assert (
            worker._conversation_accumulator is not None
        ), "Accumulator should exist after processing tasks"

        # save workflow with mocked summarization
        mock_summary_result = {
            "status": "success",
            "summary": "Test summary",
            "file_path": f"{temp_context_dir}/test_workflow.md",
        }

        with patch.object(
            ChatAgent, 'asummarize', return_value=mock_summary_result
        ):
            result = await worker.save_workflow_memories_async()

        # verify save was successful
        assert (
            result["status"] == "success"
        ), f"Save should succeed, got: {result}"

        # accumulator should be None after successful save
        assert worker._conversation_accumulator is None, (
            "Accumulator should be cleared after successful save to "
            "prevent memory leaks and duplicate content in future saves"
        )

    @pytest.mark.asyncio
    async def test_accumulator_receives_memory_not_main_worker(
        self, temp_context_dir
    ):
        """Test that conversations go to accumulator, not main worker.

        Validates the design separation - accumulator collects task
        conversations while main worker memory stays clean.
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=agent,
            enable_workflow_memory=True,
            use_agent_pool=False,  # use cloning instead of pool
        )

        # get initial main worker memory count
        main_worker_records_before = len(worker.worker.memory.retrieve())

        # process task
        task = Task(content="Process this task", id="t1")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Task completed"
            )
            await worker._process_task(task, [])

        # main worker should still have same memory (cloned agents are used)
        main_worker_records_after = len(worker.worker.memory.retrieve())
        assert main_worker_records_after == main_worker_records_before, (
            f"Main worker memory should not change "
            f"(before: {main_worker_records_before}, "
            f"after: {main_worker_records_after})"
        )

        # accumulator should have the task conversations
        accumulator = worker._conversation_accumulator
        assert accumulator is not None, "Accumulator should exist"

        accumulator_records = accumulator.memory.retrieve()
        assert len(accumulator_records) > main_worker_records_before, (
            f"Accumulator should have more records than main worker "
            f"(accumulator: {len(accumulator_records)}, "
            f"main: {main_worker_records_before})"
        )

    @pytest.mark.asyncio
    async def test_save_workflow_with_no_conversation_history(
        self, temp_context_dir
    ):
        """Test saving workflow when agent has no conversations.

        Should handle gracefully (return error or empty state) rather
        than crashing.
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=agent,
            enable_workflow_memory=True,
        )

        # don't process any tasks - no conversation history
        # accumulator should be None
        assert worker._conversation_accumulator is None

        # mock asummarize to handle the case
        mock_summary_result = {
            "status": "error",
            "message": "No conversation history to summarize",
        }

        with patch.object(
            ChatAgent, 'asummarize', return_value=mock_summary_result
        ):
            result = await worker.save_workflow_memories_async()

        # should return result with status (either success or error)
        assert "status" in result, "Result should have 'status' key"

        # if error, should have descriptive message
        if result["status"] == "error":
            assert "message" in result, "Error result should have 'message'"


class TestAgentPoolMemoryTransfer:
    """Test agent pool integration with workflow memory system."""

    @pytest.mark.asyncio
    async def test_pooled_agent_memory_transfers_to_accumulator(
        self, temp_context_dir
    ):
        """Test that conversations from pooled agents are accumulated.

        Validates the memory transfer logic from pooled agents to the
        accumulator, which is critical for the agent pooling feature.
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        base_agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=base_agent,
            use_agent_pool=True,  # enable agent pooling
            enable_workflow_memory=True,
        )

        # process task (will use pooled agent)
        task = Task(content="Calculate 2+2", id="t1")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="The answer is 4"
            )
            await worker._process_task(task, [])

        # verify accumulator received the conversation from pooled agent
        accumulator = worker._conversation_accumulator
        assert (
            accumulator is not None
        ), "Accumulator should exist when workflow memory is enabled"

        records = accumulator.memory.retrieve()
        assert len(records) >= 2, (
            f"Expected at least 2 messages (user + assistant), "
            f"got {len(records)}"
        )

        # verify the messages are about the task
        messages_content = [r.memory_record.message.content for r in records]
        assert any(
            "2+2" in msg for msg in messages_content
        ), "Should contain task content from pooled agent"

    @pytest.mark.asyncio
    async def test_memory_accumulation_with_and_without_pool(
        self, temp_context_dir
    ):
        """Test that memory accumulation works consistently with/without pool.

        Validates that the feature works identically regardless of
        pooling configuration.
        """

        def create_test_agent():
            sys_msg = BaseMessage.make_assistant_message(
                role_name="Test Worker", content="You are a test worker."
            )
            return ChatAgent(sys_msg)

        # test with pool enabled
        worker_pooled = SingleAgentWorker(
            description="test_worker",
            worker=create_test_agent(),
            use_agent_pool=True,
            enable_workflow_memory=True,
        )

        task = Task(content="Process this data", id="t1")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Data processed"
            )
            await worker_pooled._process_task(task, [])

        pooled_memory = (
            worker_pooled._conversation_accumulator.memory.retrieve()
        )

        # test with pool disabled
        worker_no_pool = SingleAgentWorker(
            description="test_worker",
            worker=create_test_agent(),
            use_agent_pool=False,
            enable_workflow_memory=True,
        )

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Data processed"
            )
            await worker_no_pool._process_task(task, [])

        no_pool_memory = (
            worker_no_pool._conversation_accumulator.memory.retrieve()
        )

        # should accumulate same number of messages
        assert len(pooled_memory) == len(no_pool_memory), (
            f"Pooled and non-pooled should accumulate same number of "
            f"messages (pooled: {len(pooled_memory)}, "
            f"non-pooled: {len(no_pool_memory)})"
        )

    @pytest.mark.asyncio
    async def test_pooled_agent_reset_after_return(self, temp_context_dir):
        """Test that pooled agents are properly reset after being returned.

        Validates memory isolation between different task executions
        using the same pooled agent.
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        base_agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=base_agent,
            use_agent_pool=True,
            enable_workflow_memory=True,
            pool_initial_size=1,  # single agent in pool
        )

        # process first task
        task1 = Task(content="First task", id="t1")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="First task done"
            )
            await worker._process_task(task1, [])

        # get accumulator state after first task
        accumulator_after_task1 = len(
            worker._conversation_accumulator.memory.retrieve()
        )

        # process second task (should reuse same pooled agent)
        task2 = Task(content="Second task", id="t2")

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant", content="Second task done"
            )
            await worker._process_task(task2, [])

        # accumulator should have more messages now
        accumulator_after_task2 = len(
            worker._conversation_accumulator.memory.retrieve()
        )

        assert accumulator_after_task2 > accumulator_after_task1, (
            "Accumulator should grow after processing second task "
            f"(after task1: {accumulator_after_task1}, "
            f"after task2: {accumulator_after_task2})"
        )

        # verify both tasks are represented in accumulator
        records = worker._conversation_accumulator.memory.retrieve()
        messages_content = [r.memory_record.message.content for r in records]

        assert any(
            "First task" in msg for msg in messages_content
        ), "Should contain first task content"
        assert any(
            "Second task" in msg for msg in messages_content
        ), "Should contain second task content"


class TestWorkflowContentValidation:
    """Test workflow content loading and formatting."""

    def test_workflow_content_actually_in_system_message(
        self, temp_context_dir
    ):
        """Test that loaded workflow content appears in system message.

        Validates end-to-end file I/O and content parsing to ensure
        workflows are properly loaded and added to agent context.
        """
        # create real workflow file with specific content
        workflow_content = """### Task Title
Data Analysis Pipeline

### Task Description
This workflow analyzes sales data using pandas and matplotlib.

### Tags
- data-analysis
- python
- visualization

### Steps
1. Load CSV file with pandas
2. Clean missing values
3. Generate summary statistics
4. Create bar chart visualization
"""

        # save to file in specific session
        session_dir = os.path.join(
            temp_context_dir, "workforce_workflows", "session_test_123"
        )
        os.makedirs(session_dir, exist_ok=True)

        workflow_file = os.path.join(session_dir, "analyst_workflow.md")
        with open(workflow_file, 'w') as f:
            f.write(workflow_content)

        # create worker and load workflow
        worker = MockSingleAgentWorker("data_analyst")
        original_system = worker.worker._system_message.content

        # load workflow from the specific session
        result = worker.load_workflow_memories(session_id="session_test_123")
        assert result is True, "Workflow load should succeed"

        # verify system message contains workflow content
        updated_system = worker.worker._system_message.content
        assert (
            updated_system != original_system
        ), "System message should be modified"
        assert (
            "Data Analysis Pipeline" in updated_system
        ), "Should contain task title"
        assert (
            "pandas and matplotlib" in updated_system
        ), "Should contain task description content"
        assert (
            "Load CSV file" in updated_system
        ), "Should contain workflow steps"

        # verify proper formatting with header
        assert (
            "Previous Workflows" in updated_system
        ), "Should have workflows header"
        assert "=" * 60 in updated_system, "Should have separator lines"

    def test_multiple_workflows_formatted_correctly(self, temp_context_dir):
        """Test that multiple workflows are formatted with correct headers.

        Validates plural formatting and proper separation of multiple
        workflow entries by directly testing the formatting method.
        """
        # test the formatting method directly with mock workflow data

        worker = MockSingleAgentWorker("test_worker")
        manager = worker._get_workflow_manager()

        # create mock workflow data
        workflows_to_load = [
            {
                'filename': 'workflow_1',
                'content': """### Task Title
First Workflow

### Description
This is the first workflow.""",
            },
            {
                'filename': 'workflow_2',
                'content': """### Task Title
Second Workflow

### Description
This is the second workflow.""",
            },
            {
                'filename': 'workflow_3',
                'content': """### Task Title
Third Workflow

### Description
This is the third workflow.""",
            },
        ]

        # test the formatting method directly
        formatted_content = manager._format_workflows_for_context(
            workflows_to_load
        )

        # verify formatting
        assert (
            "3 previous" in formatted_content.lower()
            or "3" in formatted_content
        ), "Should indicate 3 workflows"
        assert "Previous Workflows" in formatted_content, "Should have header"

        # each workflow should be numbered
        assert "Workflow 1:" in formatted_content
        assert "Workflow 2:" in formatted_content
        assert "Workflow 3:" in formatted_content

        # all content should be present
        assert "First Workflow" in formatted_content
        assert "Second Workflow" in formatted_content
        assert "Third Workflow" in formatted_content

        # should have separators
        separator_count = formatted_content.count("=" * 60)
        assert (
            separator_count >= 3
        ), f"Should have at least 3 separators, got {separator_count}"

    def test_metadata_filtered_from_loaded_workflow(self, temp_context_dir):
        """Test that metadata section is not included in system message.

        Validates that metadata is properly filtered to avoid polluting
        agent context with irrelevant session info.
        """
        # create workflow with metadata section
        workflow_with_metadata = """## Metadata

- session_id: test_session_456
- created_at: 2025-01-01
- agent_id: test-agent-789

## WorkflowSummary

### Task Title
Actual Workflow Content

### Description
This is the actual workflow description that should be loaded.

### Steps
1. Do important work
2. Complete the task
"""

        # save to file
        session_dir = os.path.join(
            temp_context_dir, "workforce_workflows", "session_metadata_test"
        )
        os.makedirs(session_dir, exist_ok=True)

        workflow_file = os.path.join(session_dir, "test_workflow.md")
        with open(workflow_file, 'w') as f:
            f.write(workflow_with_metadata)

        # load workflow
        worker = MockSingleAgentWorker("test_worker")
        result = worker.load_workflow_memories(
            session_id="session_metadata_test"
        )
        assert result is True, "Workflow with metadata should load"

        # verify system message
        system_content = worker.worker._system_message.content

        # should contain actual workflow content
        assert (
            "Actual Workflow Content" in system_content
        ), "Should contain workflow title"
        assert (
            "actual workflow description" in system_content
        ), "Should contain workflow description"
        assert (
            "Do important work" in system_content
        ), "Should contain workflow steps"

        # should NOT contain metadata
        assert (
            "session_id: test_session_456" not in system_content
        ), "Should filter out session_id metadata"
        assert (
            "agent_id: test-agent-789" not in system_content
        ), "Should filter out agent_id metadata"
        assert (
            "created_at: 2025-01-01" not in system_content
        ), "Should filter out created_at metadata"


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in workflow memory system."""

    def test_load_workflow_with_corrupted_markdown(self, temp_context_dir):
        """Test loading workflow from corrupted/malformed file.

        Should handle gracefully without crashing.
        """
        # create file with malformed content (not valid markdown structure)
        corrupted_content = """This is just random text
        with no proper structure
        ### Missing proper headers
        No Task Title section
        Random characters: !@#$%^&*()
        """

        # save corrupted file
        session_dir = os.path.join(
            temp_context_dir, "workforce_workflows", "session_corrupted"
        )
        os.makedirs(session_dir, exist_ok=True)

        corrupted_file = os.path.join(session_dir, "corrupted_workflow.md")
        with open(corrupted_file, 'w') as f:
            f.write(corrupted_content)

        # attempt to load - should not crash
        worker = MockSingleAgentWorker("test_worker")

        try:
            # loading may succeed or fail gracefully, but should not crash
            result = worker.load_workflow_memories(
                session_id="session_corrupted"
            )

            # if it succeeds, verify it handled the content
            if result is True:
                # system message should be updated even with malformed content
                system_content = worker.worker._system_message.content
                # the content might be loaded as-is, which is acceptable
                assert isinstance(
                    system_content, str
                ), "System message should still be a string"

        except Exception as e:
            # if it raises an exception, it should be a handled one
            # (not a crash like AttributeError or KeyError)
            pytest.fail(
                f"Loading corrupted workflow should handle errors gracefully, "
                f"but got unhandled exception: {type(e).__name__}: {e}"
            )

    def test_workflow_operations_without_camel_workdir(self):
        """Test that workflows work when CAMEL_WORKDIR is not set.

        Should use default "workforce_workflows" directory.
        """
        # save current env var if it exists
        original_workdir = os.environ.get("CAMEL_WORKDIR")

        try:
            # remove CAMEL_WORKDIR env var
            if "CAMEL_WORKDIR" in os.environ:
                del os.environ["CAMEL_WORKDIR"]

            # create worker and test operations
            worker = MockSingleAgentWorker("test_worker")

            # should be able to create workflow manager without error
            manager = worker._get_workflow_manager()
            assert (
                manager is not None
            ), "Workflow manager should be created without CAMEL_WORKDIR"

            # context utility should use default directory
            context_util = manager._get_context_utility()
            assert (
                context_util is not None
            ), "Context utility should be created with default directory"

            # the context directory should use default "workforce_workflows"
            # (we don't test actual file operations to avoid creating files
            # in unexpected locations)

        finally:
            # restore original env var
            if original_workdir is not None:
                os.environ["CAMEL_WORKDIR"] = original_workdir
            elif "CAMEL_WORKDIR" in os.environ:
                del os.environ["CAMEL_WORKDIR"]

    @pytest.mark.asyncio
    async def test_save_workflow_with_very_long_conversation(
        self, temp_context_dir
    ):
        """Test workflow saving with very long conversation.

        Should handle large conversations gracefully (may truncate or
        summarize effectively).
        """
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Test Worker", content="You are a test worker."
        )
        agent = ChatAgent(sys_msg)
        worker = SingleAgentWorker(
            description="test_worker",
            worker=agent,
            enable_workflow_memory=True,
            use_agent_pool=False,
        )

        # create many tasks to generate long conversation
        tasks = [
            Task(content=f"Task {i}: " + "x" * 100, id=f"t{i}")
            for i in range(50)  # 50 tasks with long content
        ]

        with patch.object(ChatAgent, 'step') as mock_step:
            mock_step.return_value = BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Task completed with long response " + "y" * 100,
            )

            # process all tasks
            for task in tasks:
                await worker._process_task(task, [])

        # verify accumulator has many messages
        accumulator = worker._conversation_accumulator
        assert accumulator is not None
        records = accumulator.memory.retrieve()
        assert (
            len(records) > 50
        ), f"Should have many records (>50), got {len(records)}"

        # attempt to save - should handle gracefully
        mock_summary_result = {
            "status": "success",
            "summary": "Summary of very long conversation",
            "file_path": f"{temp_context_dir}/long_conversation_workflow.md",
        }

        with patch.object(
            ChatAgent, 'asummarize', return_value=mock_summary_result
        ):
            result = await worker.save_workflow_memories_async()

        # should succeed or return informative error
        assert "status" in result, "Result should have status"

        if result["status"] == "success":
            # successful handling
            assert "summary" in result
        elif result["status"] == "error":
            # graceful error handling
            assert "message" in result
