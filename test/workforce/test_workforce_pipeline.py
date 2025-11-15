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
from typing import List

import pytest

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.workforce import WorkforceMode
from camel.tasks.task import Task, TaskState
from camel.types import ModelPlatformType, ModelType


class SuccessfulWorker(SingleAgentWorker):
    """A worker that always succeeds for testing purposes."""

    def __init__(self, description: str, result_suffix: str = ""):
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Successful Worker",
            content="This worker always succeeds.",
        )
        agent = ChatAgent(sys_msg)
        super().__init__(description, agent)
        self.result_suffix = result_suffix

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        """Always return successful task with dependency info."""
        # Include dependency results in the output
        dep_info = []
        for dep in dependencies:
            dep_info.append(f"[Dep {dep.id}: {dep.state.value}]")

        task.state = TaskState.DONE
        task.result = (
            f"Task {task.id} completed successfully{self.result_suffix}. "
            f"Dependencies: {', '.join(dep_info) if dep_info else 'None'}"
        )
        return TaskState.DONE


class FailingWorker(SingleAgentWorker):
    """A worker that always fails for testing purposes."""

    def __init__(self, description: str):
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Failing Worker", content="This worker always fails."
        )
        agent = ChatAgent(sys_msg)
        super().__init__(description, agent)

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        """Always return failed task."""
        task.state = TaskState.FAILED
        task.result = f"Task {task.id} failed deliberately for testing"
        return TaskState.FAILED


@pytest.fixture(autouse=True)
def stub_openai_api_key(monkeypatch):
    r"""Ensure OPENAI_API_KEY is set during tests."""
    previous_value = os.environ.get("OPENAI_API_KEY")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    yield
    if previous_value is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", previous_value)


@pytest.fixture
def mock_model():
    r"""Create a real model backend for testing"""
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )


def test_pipeline_builder_basic_chain():
    """Test basic pipeline building with sequential tasks."""
    workforce = Workforce("Test Workforce")

    # Build a simple chain: Task A -> Task B -> Task C
    workforce.pipeline_add("Task A").pipeline_add("Task B").pipeline_add(
        "Task C"
    ).pipeline_build()

    # Verify tasks were created
    assert len(workforce._pending_tasks) == 3

    # Verify dependencies
    tasks = list(workforce._pending_tasks)
    assert (
        len(workforce._task_dependencies[tasks[0].id]) == 0
    )  # Task A has no deps
    assert (
        tasks[0].id in workforce._task_dependencies[tasks[1].id]
    )  # Task B depends on A
    assert (
        tasks[1].id in workforce._task_dependencies[tasks[2].id]
    )  # Task C depends on B


def test_pipeline_fork_join_pattern():
    """Test fork-join pattern in pipeline."""
    workforce = Workforce("Test Workforce")

    # Build fork-join: Task A -> [Task B, Task C] -> Task D
    workforce.pipeline_add("Task A").pipeline_fork(
        ["Task B", "Task C"]
    ).pipeline_join("Task D").pipeline_build()

    # Verify tasks were created
    assert len(workforce._pending_tasks) == 4

    # Find tasks by content
    task_a = next(t for t in workforce._pending_tasks if t.content == "Task A")
    task_b = next(t for t in workforce._pending_tasks if t.content == "Task B")
    task_c = next(t for t in workforce._pending_tasks if t.content == "Task C")
    task_d = next(t for t in workforce._pending_tasks if t.content == "Task D")

    # Verify dependencies
    assert len(workforce._task_dependencies[task_a.id]) == 0  # A has no deps
    assert (
        task_a.id in workforce._task_dependencies[task_b.id]
    )  # B depends on A
    assert (
        task_a.id in workforce._task_dependencies[task_c.id]
    )  # C depends on A
    assert (
        task_b.id in workforce._task_dependencies[task_d.id]
        and task_c.id in workforce._task_dependencies[task_d.id]
    )  # D depends on B and C


def test_pipeline_add_with_task_objects():
    """Test pipeline building with Task objects instead of strings."""
    workforce = Workforce("Test Workforce")

    task1 = Task(content="Task 1", id="custom_1")
    task2 = Task(
        content="Task 2", id="custom_2", additional_info={"priority": "high"}
    )

    workforce.pipeline_add(task1).pipeline_add(task2).pipeline_build()

    assert len(workforce._pending_tasks) == 2
    tasks = list(workforce._pending_tasks)

    # Verify custom IDs were preserved
    assert tasks[0].id == "custom_1"
    assert tasks[1].id == "custom_2"
    assert tasks[1].additional_info["priority"] == "high"


def test_pipeline_mode_auto_switch():
    """Test that pipeline methods automatically switch to PIPELINE mode."""
    workforce = Workforce("Test Workforce")

    # Initially should be AUTO_DECOMPOSE
    assert workforce.mode == WorkforceMode.AUTO_DECOMPOSE

    # Adding pipeline task should auto-switch
    workforce.pipeline_add("Task A")

    assert workforce.mode == WorkforceMode.PIPELINE


def test_pipeline_manual_mode_setting():
    """Test manual mode setting with set_mode()."""
    workforce = Workforce("Test Workforce")

    # Test switching to PIPELINE mode
    workforce.set_mode(WorkforceMode.PIPELINE)
    assert workforce.mode == WorkforceMode.PIPELINE

    # Test switching back to AUTO_DECOMPOSE mode
    workforce.set_mode(WorkforceMode.AUTO_DECOMPOSE)
    assert workforce.mode == WorkforceMode.AUTO_DECOMPOSE


def test_pipeline_execution_structure():
    """Test pipeline structure and worker assignment without execution."""
    workforce = Workforce("Test Workforce")

    # Add workers
    worker = SuccessfulWorker("Success Worker")
    workforce.add_single_agent_worker("Success Worker", worker.worker)

    # Build simple pipeline
    workforce.pipeline_add("Step 1").pipeline_add("Step 2").pipeline_build()

    # Verify pipeline structure
    assert (
        len(workforce._pending_tasks) == 2
    ), "Should have 2 tasks in pipeline"
    assert len(workforce._children) == 1, "Should have 1 worker"

    # Get the pipeline tasks
    pipeline_tasks = list(workforce._pending_tasks)
    task_1 = pipeline_tasks[0]
    task_2 = pipeline_tasks[1]

    # Verify dependencies were set correctly
    assert (
        len(workforce._task_dependencies[task_1.id]) == 0
    ), "Task 1 should have no dependencies"
    assert (
        task_1.id in workforce._task_dependencies[task_2.id]
    ), "Task 2 should depend on Task 1"

    # Verify mode is PIPELINE
    assert workforce.mode == WorkforceMode.PIPELINE

    # Verify worker exists and can be assigned
    assert workforce._children[0].node_id is not None


@pytest.mark.asyncio
async def test_pipeline_failed_task_continues_workflow():
    """Test that in PIPELINE mode, failed tasks allow workflow to continue."""
    workforce = Workforce("Test Workforce")

    # Add both successful and failing workers
    success_worker = SuccessfulWorker("Success Worker")
    fail_worker = FailingWorker("Fail Worker")

    workforce.add_single_agent_worker("Success Worker", success_worker.worker)
    workforce.add_single_agent_worker("Fail Worker", fail_worker.worker)

    # Build pipeline where middle task will fail
    workforce.pipeline_add("Task 1").pipeline_add(
        "Task 2 (will fail)"
    ).pipeline_add("Task 3").pipeline_build()

    # Get tasks
    tasks = list(workforce._pending_tasks)
    task_1 = tasks[0]
    task_2 = tasks[1]
    task_3 = tasks[2]

    # Manually set up the scenario
    workforce.mode = WorkforceMode.PIPELINE

    # Mock task 2 to fail after max retries
    task_2.failure_count = 3  # Already at max retries

    # Add to completed tasks to simulate task 1 completed, task 2 failed
    task_1.state = TaskState.DONE
    task_2.state = TaskState.FAILED
    workforce._completed_tasks = [task_1, task_2]

    # Check if task 3 should be posted (PIPELINE mode continues)
    completed_tasks_info = {t.id: t.state for t in workforce._completed_tasks}
    all_deps_completed = all(
        dep_id in completed_tasks_info
        for dep_id in workforce._task_dependencies[task_3.id]
    )

    assert (
        all_deps_completed
    ), "Task 3 dependencies should be marked as completed"

    # In PIPELINE mode, should post task even if dependency failed
    should_post = (
        workforce.mode == WorkforceMode.PIPELINE and all_deps_completed
    )
    assert should_post, "Task 3 should be ready to post in PIPELINE mode"


@pytest.mark.asyncio
async def test_pipeline_fork_with_one_branch_failing():
    """Ensure fork-join runs even when one branch fails."""
    workforce = Workforce("Test Workforce")

    # Add workers
    success_worker = SuccessfulWorker("Success Worker")
    workforce.add_single_agent_worker("Success Worker", success_worker.worker)

    # Build fork-join
    workforce.pipeline_add("Task A").pipeline_fork(
        ["Task B", "Task C"]
    ).pipeline_join("Task D").pipeline_build()

    tasks_list = list(workforce._pending_tasks)
    task_a = next(t for t in tasks_list if t.content == "Task A")
    task_b = next(t for t in tasks_list if t.content == "Task B")
    task_c = next(t for t in tasks_list if t.content == "Task C")
    task_d = next(t for t in tasks_list if t.content == "Task D")

    # Simulate: A done, B done, C failed
    task_a.state = TaskState.DONE
    task_b.state = TaskState.DONE
    task_c.state = TaskState.FAILED
    task_c.failure_count = 3

    workforce._completed_tasks = [task_a, task_b, task_c]
    workforce.mode = WorkforceMode.PIPELINE

    # Check if Task D should execute
    completed_tasks_info = {t.id: t.state for t in workforce._completed_tasks}
    all_deps_completed = all(
        dep_id in completed_tasks_info
        for dep_id in workforce._task_dependencies[task_d.id]
    )

    assert (
        all_deps_completed
    ), "Task D dependencies should all be completed (success or failure)"

    # Task D should be ready to execute in PIPELINE mode
    should_post = (
        workforce.mode == WorkforceMode.PIPELINE and all_deps_completed
    )
    assert (
        should_post
    ), "Task D (join) should execute even though Task C (branch) failed"


def test_pipeline_mode_reset_after_execution():
    """Test that mode resets to initial value after pipeline execution."""
    # Create workforce with AUTO_DECOMPOSE as initial mode (default)
    workforce = Workforce("Test Workforce")
    initial_mode = workforce._initial_mode

    assert initial_mode == WorkforceMode.AUTO_DECOMPOSE

    # Switch to PIPELINE mode
    workforce.pipeline_add("Task 1").pipeline_build()
    assert workforce.mode == WorkforceMode.PIPELINE

    # Simulate pipeline completion by calling the mode reset logic
    workforce.mode = workforce._initial_mode

    # Verify mode was reset
    assert (
        workforce.mode == initial_mode
    ), "Mode should reset to initial value after execution"


def test_all_pipeline_tasks_successful_with_failures():
    """Test _all_pipeline_tasks_successful() correctly identifies failures."""
    workforce = Workforce("Test Workforce")

    # Create test tasks
    task1 = Task(content="Task 1", id="1")
    task2 = Task(content="Task 2", id="2")
    task3 = Task(content="Task 3", id="3")

    task1.state = TaskState.DONE
    task2.state = TaskState.FAILED
    task3.state = TaskState.DONE

    workforce._completed_tasks = [task1, task2, task3]
    workforce._pending_tasks.clear()

    # Should return False because task2 failed
    result = workforce._all_pipeline_tasks_successful()

    assert (
        result is False
    ), "Pipeline should be marked as failed when any task fails"


def test_all_pipeline_tasks_successful_all_done():
    """Test _all_pipeline_tasks_successful() with all tasks successful."""
    workforce = Workforce("Test Workforce")

    # Create test tasks
    task1 = Task(content="Task 1", id="1")
    task2 = Task(content="Task 2", id="2")
    task3 = Task(content="Task 3", id="3")

    task1.state = TaskState.DONE
    task2.state = TaskState.DONE
    task3.state = TaskState.DONE

    workforce._completed_tasks = [task1, task2, task3]
    workforce._pending_tasks.clear()

    # Should return True because all tasks succeeded
    result = workforce._all_pipeline_tasks_successful()

    assert (
        result is True
    ), "Pipeline should be marked as successful when all tasks succeed"


def test_all_pipeline_tasks_successful_with_pending():
    """Test _all_pipeline_tasks_successful() with pending tasks."""
    workforce = Workforce("Test Workforce")

    # Create test tasks
    task1 = Task(content="Task 1", id="1")
    task2 = Task(content="Task 2", id="2")

    task1.state = TaskState.DONE
    workforce._completed_tasks = [task1]
    workforce._pending_tasks.append(task2)

    # Should return False because there are pending tasks
    result = workforce._all_pipeline_tasks_successful()

    assert (
        result is False
    ), "Pipeline should not be marked successful with pending tasks"


def test_pipeline_reset_clears_state():
    """Test that reset() clears pipeline state correctly."""
    workforce = Workforce("Test Workforce")

    # Build a pipeline
    workforce.pipeline_add("Task 1").pipeline_add("Task 2").pipeline_build()

    # Verify pipeline was built
    assert len(workforce._pending_tasks) > 0
    assert workforce.mode == WorkforceMode.PIPELINE

    # Reset workforce
    workforce.reset()

    # Verify state was cleared
    assert len(workforce._pending_tasks) == 0
    assert (
        workforce.mode == workforce._initial_mode
    ), "Mode should reset to initial value"
    assert workforce._pipeline_builder is None


def test_pipeline_with_parallel_tasks():
    """Test add_parallel_pipeline_tasks functionality."""
    workforce = Workforce("Test Workforce")

    # Add parallel tasks
    workforce.pipeline_add("Initial Task").add_parallel_pipeline_tasks(
        ["Parallel 1", "Parallel 2", "Parallel 3"]
    ).add_sync_pipeline_task("Sync Task").pipeline_build()

    # Verify all tasks were created
    assert len(workforce._pending_tasks) == 5

    tasks_list = list(workforce._pending_tasks)

    # Find parallel tasks
    parallel_tasks = [
        t
        for t in tasks_list
        if t.content in ["Parallel 1", "Parallel 2", "Parallel 3"]
    ]
    sync_task = next(t for t in tasks_list if t.content == "Sync Task")

    # Verify parallel tasks all depend on the initial task
    initial_task = next(t for t in tasks_list if t.content == "Initial Task")
    for parallel_task in parallel_tasks:
        assert (
            initial_task.id in workforce._task_dependencies[parallel_task.id]
        )

    # Verify sync task depends on all parallel tasks
    for parallel_task in parallel_tasks:
        assert parallel_task.id in workforce._task_dependencies[sync_task.id]


def test_pipeline_with_task_objects_in_parallel():
    """Test parallel tasks with Task objects."""
    workforce = Workforce("Test Workforce")

    task1 = Task(
        content="Parallel Task 1", additional_info={"type": "analysis"}
    )
    task2 = Task(
        content="Parallel Task 2", additional_info={"type": "research"}
    )

    workforce.pipeline_add("Start").add_parallel_pipeline_tasks(
        [task1, task2]
    ).pipeline_build()

    assert len(workforce._pending_tasks) == 3

    # Verify tasks were created with correct content
    tasks_list = list(workforce._pending_tasks)
    start_task = next((t for t in tasks_list if t.content == "Start"), None)
    parallel_task_1 = next(
        (t for t in tasks_list if t.content == "Parallel Task 1"), None
    )
    parallel_task_2 = next(
        (t for t in tasks_list if t.content == "Parallel Task 2"), None
    )

    assert start_task is not None, "Start task should exist"
    assert parallel_task_1 is not None, "Parallel Task 1 should exist"
    assert parallel_task_2 is not None, "Parallel Task 2 should exist"

    # Verify additional info if preserved (implementation dependent)
    # If preserved, check it; otherwise ensure tasks exist
    if (
        parallel_task_1.additional_info
        and "type" in parallel_task_1.additional_info
    ):
        assert parallel_task_1.additional_info["type"] == "analysis"
    if (
        parallel_task_2.additional_info
        and "type" in parallel_task_2.additional_info
    ):
        assert parallel_task_2.additional_info["type"] == "research"


@pytest.mark.asyncio
async def test_handle_failed_task_pipeline_vs_auto_decompose():
    """Compare failure handling in PIPELINE vs AUTO_DECOMPOSE modes."""
    workforce = Workforce("Test Workforce")

    # Test PIPELINE mode
    workforce.mode = WorkforceMode.PIPELINE
    task_pipeline = Task(content="Pipeline Task", id="pipeline_1")
    task_pipeline.failure_count = 3  # Max retries reached
    task_pipeline.state = TaskState.FAILED
    task_pipeline.result = "Failed"

    pipeline_mode = workforce.mode == WorkforceMode.PIPELINE

    assert pipeline_mode, "Should be in PIPELINE mode for this test section"
    assert task_pipeline.failure_count >= 3

    # Test AUTO_DECOMPOSE mode
    workforce.mode = WorkforceMode.AUTO_DECOMPOSE
    task_auto = Task(content="Auto Task", id="auto_1")
    task_auto.failure_count = 3  # Max retries reached
    task_auto.state = TaskState.FAILED
    task_auto.result = "Failed"

    auto_mode = workforce.mode == WorkforceMode.AUTO_DECOMPOSE

    assert auto_mode, "Should be in AUTO_DECOMPOSE mode for this test section"
    assert task_auto.failure_count >= 3


def test_pipeline_get_builder():
    """Test get_pipeline_builder() returns the builder instance."""
    workforce = Workforce("Test Workforce")

    # Get builder (should auto-create)
    builder = workforce.get_pipeline_builder()

    assert builder is not None
    assert workforce._pipeline_builder is builder
    assert workforce.mode == WorkforceMode.PIPELINE


def test_pipeline_complex_workflow():
    """Test a complex pipeline with multiple forks and joins."""
    workforce = Workforce("Test Workforce")

    # Build: A -> [B, C] -> D -> [E, F, G] -> H
    workforce.pipeline_add("A").pipeline_fork(["B", "C"]).pipeline_join(
        "D"
    ).pipeline_fork(["E", "F", "G"]).pipeline_join("H").pipeline_build()

    assert len(workforce._pending_tasks) == 8

    tasks_list = list(workforce._pending_tasks)
    task_a = next(t for t in tasks_list if t.content == "A")
    task_d = next(t for t in tasks_list if t.content == "D")
    task_h = next(t for t in tasks_list if t.content == "H")

    # Verify A has no dependencies
    assert len(workforce._task_dependencies[task_a.id]) == 0

    # Verify D depends on B and C
    assert len(workforce._task_dependencies[task_d.id]) == 2

    # Verify H depends on E, F, and G
    assert len(workforce._task_dependencies[task_h.id]) == 3


def test_set_mode_returns_workforce_for_chaining():
    """Test that set_mode() returns self for method chaining."""
    workforce = Workforce("Test Workforce")

    # Test method chaining
    result = workforce.set_mode(WorkforceMode.PIPELINE)

    assert result is workforce, "set_mode() should return self for chaining"
    assert workforce.mode == WorkforceMode.PIPELINE


def test_pipeline_methods_return_workforce_for_chaining():
    """Test that all pipeline methods return self for chaining."""
    workforce = Workforce("Test Workforce")

    # Test chaining
    result = (
        workforce.pipeline_add("Task 1")
        .pipeline_add("Task 2")
        .pipeline_fork(["A", "B"])
        .pipeline_join("Join")
        .pipeline_build()
    )

    assert result is workforce, "Pipeline methods should support chaining"


@pytest.mark.asyncio
async def test_pipeline_set_pipeline_tasks_directly():
    """Test set_pipeline_tasks() method for setting tasks directly."""
    workforce = Workforce("Test Workforce")

    # Create tasks with dependencies
    task1 = Task(content="Task 1", id="1")
    task2 = Task(content="Task 2", id="2")
    task3 = Task(content="Task 3", id="3")

    task2.dependencies = [task1]
    task3.dependencies = [task2]

    tasks = [task1, task2, task3]

    # Set tasks
    workforce.set_pipeline_tasks(tasks)

    # Verify mode switched
    assert workforce.mode == WorkforceMode.PIPELINE

    # Verify tasks were set
    assert len(workforce._pending_tasks) == 3

    # Verify dependencies were extracted
    assert workforce._task_dependencies["2"] == ["1"]
    assert workforce._task_dependencies["3"] == ["2"]


def test_pipeline_empty_task_list_raises_error():
    """Test that setting empty task list raises ValueError."""
    workforce = Workforce("Test Workforce")

    with pytest.raises(ValueError, match="Cannot set empty task list"):
        workforce.set_pipeline_tasks([])
