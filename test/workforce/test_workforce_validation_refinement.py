# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
"""Tests for workforce validation and refinement functionality.

This module tests the validation refinement feature that allows workforce
to validate aggregated results from parallel subtasks and refine them
if requirements are not met.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce.prompts import (
    VALIDATION_PROMPT,
    VALIDATION_RESPONSE_FORMAT,
)
from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.societies.workforce.utils import (
    RecoveryStrategy,
    TaskAnalysisResult,
    ValidationResult,
)
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task, TaskState
from camel.types import ModelPlatformType, ModelType


class TestValidationResult:
    """Tests for the ValidationResult model."""

    def test_validation_result_basic_creation(self):
        """Test basic creation of ValidationResult."""
        result = ValidationResult(
            requirements_met=True,
            unique_count=5,
            duplicate_count=2,
            missing_count=0,
            deduplicated_result="5 unique papers found",
            reasoning="All requirements met after deduplication",
        )

        assert result.requirements_met is True
        assert result.unique_count == 5
        assert result.duplicate_count == 2
        assert result.missing_count == 0
        assert result.deduplicated_result == "5 unique papers found"
        assert "requirements met" in result.reasoning.lower()
        assert result.additional_task_guidance is None
        assert result.duplicate_subtask_ids is None

    def test_validation_result_with_guidance(self):
        """Test ValidationResult with additional guidance for refinement."""
        result = ValidationResult(
            requirements_met=False,
            unique_count=3,
            duplicate_count=4,
            missing_count=2,
            deduplicated_result="3 unique papers found",
            reasoning="Only 3 unique papers found, need 2 more",
            additional_task_guidance=(
                "Find ONE unique research paper, excluding: Paper A, Paper B"
            ),
            duplicate_subtask_ids=["task_1.2", "task_1.5"],
        )

        assert result.requirements_met is False
        assert result.unique_count == 3
        assert result.missing_count == 2
        assert result.additional_task_guidance is not None
        assert "excluding" in result.additional_task_guidance
        assert result.duplicate_subtask_ids == ["task_1.2", "task_1.5"]

    def test_validation_result_default_values(self):
        """Test ValidationResult with default values."""
        result = ValidationResult(
            requirements_met=True,
            unique_count=5,
            deduplicated_result="Content here",
            reasoning="Validation complete",
        )

        assert result.duplicate_count == 0
        assert result.missing_count == 0
        assert result.additional_task_guidance is None
        assert result.duplicate_subtask_ids is None

    def test_validation_result_empty_duplicate_ids(self):
        """Test ValidationResult with empty duplicate IDs list."""
        result = ValidationResult(
            requirements_met=True,
            unique_count=5,
            duplicate_count=0,
            missing_count=0,
            deduplicated_result="All unique content",
            reasoning="No duplicates found",
            duplicate_subtask_ids=[],
        )

        assert result.duplicate_subtask_ids == []


class TestRecoveryStrategyRefine:
    """Tests for the REFINE recovery strategy."""

    def test_refine_strategy_exists(self):
        """Test that REFINE is a valid recovery strategy."""
        assert hasattr(RecoveryStrategy, 'REFINE')
        assert RecoveryStrategy.REFINE.value == "refine"

    def test_refine_strategy_string_conversion(self):
        """Test string conversion of REFINE strategy."""
        assert str(RecoveryStrategy.REFINE) == "refine"

    def test_refine_strategy_repr(self):
        """Test repr of REFINE strategy."""
        assert repr(RecoveryStrategy.REFINE) == "RecoveryStrategy.REFINE"

    def test_all_recovery_strategies(self):
        """Test that all expected recovery strategies exist."""
        expected_strategies = [
            'RETRY',
            'REPLAN',
            'DECOMPOSE',
            'CREATE_WORKER',
            'REASSIGN',
            'REFINE',
        ]
        for strategy in expected_strategies:
            assert hasattr(RecoveryStrategy, strategy)


class TestValidationPrompt:
    """Tests for the VALIDATION_PROMPT template."""

    def test_validation_prompt_exists(self):
        """Test that VALIDATION_PROMPT is defined."""
        assert VALIDATION_PROMPT is not None

    def test_validation_prompt_format_placeholders(self):
        """Test that VALIDATION_PROMPT has required format placeholders."""
        prompt_str = str(VALIDATION_PROMPT)
        assert "{task_id}" in prompt_str
        assert "{task_content}" in prompt_str
        assert "{num_subtasks}" in prompt_str
        assert "{subtask_ids}" in prompt_str
        assert "{aggregated_result}" in prompt_str
        assert "{response_format}" in prompt_str

    def test_validation_prompt_can_format(self):
        """Test that VALIDATION_PROMPT can be formatted."""
        formatted = VALIDATION_PROMPT.format(
            task_id="test_task_1",
            task_content="Find 5 papers",
            num_subtasks=5,
            subtask_ids="task_1.1, task_1.2, task_1.3",
            aggregated_result="Paper 1, Paper 2, Paper 3",
            response_format=VALIDATION_RESPONSE_FORMAT,
        )

        assert "test_task_1" in formatted
        assert "Find 5 papers" in formatted
        assert "task_1.1" in formatted

    def test_validation_response_format_exists(self):
        """Test that VALIDATION_RESPONSE_FORMAT is defined."""
        assert VALIDATION_RESPONSE_FORMAT is not None
        assert "requirements_met" in VALIDATION_RESPONSE_FORMAT
        assert "unique_count" in VALIDATION_RESPONSE_FORMAT
        assert "duplicate_count" in VALIDATION_RESPONSE_FORMAT
        assert "deduplicated_result" in VALIDATION_RESPONSE_FORMAT


class TestStructuredOutputHandlerValidation:
    """Tests for StructuredOutputHandler with ValidationResult."""

    def test_create_default_validation_result(self):
        """Test creating default ValidationResult instance."""
        handler = StructuredOutputHandler()
        default = handler._create_default_instance(ValidationResult)

        assert isinstance(default, ValidationResult)
        assert default.requirements_met is False
        assert default.unique_count == 0
        assert default.deduplicated_result == ""
        assert "parsing error" in default.reasoning.lower()

    def test_create_fallback_validation_result(self):
        """Test creating fallback ValidationResult with error message."""
        handler = StructuredOutputHandler()
        fallback = handler.create_fallback_response(
            ValidationResult, "Test error message"
        )

        assert isinstance(fallback, ValidationResult)
        assert fallback.requirements_met is False
        assert "Test error message" in fallback.reasoning

    def test_fix_common_issues_validation_result(self):
        """Test fixing common issues in ValidationResult data."""
        data = {
            "requirements_met": True,
            "unique_count": 5,
            "deduplicated_result": {
                "items": ["a", "b"]
            },  # dict instead of str
            "reasoning": "Test",
        }

        fixed = StructuredOutputHandler._fix_common_issues(
            data, ValidationResult
        )

        assert isinstance(fixed["deduplicated_result"], str)

    def test_parse_validation_result_from_json(self):
        """Test parsing ValidationResult from JSON response."""
        handler = StructuredOutputHandler()
        json_response = '''```json
{
    "requirements_met": true,
    "unique_count": 5,
    "duplicate_count": 0,
    "missing_count": 0,
    "deduplicated_result": "5 papers found",
    "reasoning": "All requirements met",
    "additional_task_guidance": null,
    "duplicate_subtask_ids": null
}
```'''

        result = handler.parse_structured_response(
            json_response, ValidationResult
        )

        assert isinstance(result, ValidationResult)
        assert result.requirements_met is True
        assert result.unique_count == 5

    def test_parse_validation_result_with_fallback(self):
        """Test parsing ValidationResult with fallback on invalid input."""
        handler = StructuredOutputHandler()
        invalid_response = "This is not valid JSON"

        result = handler.parse_structured_response(
            invalid_response,
            ValidationResult,
            fallback_values={
                "requirements_met": False,
                "unique_count": 0,
                "deduplicated_result": "fallback",
                "reasoning": "fallback reason",
            },
        )

        assert isinstance(result, ValidationResult)
        assert result.requirements_met is False


class TestTaskAnalysisResultWithRefine:
    """Tests for TaskAnalysisResult with REFINE strategy."""

    def test_task_analysis_result_with_refine_strategy(self):
        """Test creating TaskAnalysisResult with REFINE strategy."""
        result = TaskAnalysisResult(
            reasoning="Need to refine parallel task results",
            recovery_strategy=RecoveryStrategy.REFINE,
            modified_task_content=None,
            issues=["Missing 2 items to meet requirements"],
        )

        assert result.recovery_strategy == RecoveryStrategy.REFINE
        assert "refine" in result.reasoning.lower()
        assert len(result.issues) == 1


@pytest.fixture
def mock_model():
    """Create a mock model for testing."""
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )


@pytest.fixture
def workforce_with_refinement(mock_model):
    """Create a workforce with refinement enabled."""
    coordinator_agent = ChatAgent(
        "You are a helpful coordinator.", model=mock_model
    )
    task_agent = ChatAgent("You are a helpful task planner.", model=mock_model)

    workforce = Workforce(
        description="Test Workforce with Refinement",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        max_refinement_iterations=2,
    )
    return workforce


class TestWorkforceRefinementInit:
    """Tests for Workforce initialization with refinement parameters."""

    def test_workforce_max_refinement_iterations_default(self, mock_model):
        """Test default max_refinement_iterations value."""
        coordinator_agent = ChatAgent(
            "You are a coordinator.", model=mock_model
        )
        task_agent = ChatAgent("You are a planner.", model=mock_model)

        workforce = Workforce(
            description="Test Workforce",
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
        )

        assert workforce.max_refinement_iterations == 2

    def test_workforce_max_refinement_iterations_custom(self, mock_model):
        """Test custom max_refinement_iterations value."""
        coordinator_agent = ChatAgent(
            "You are a coordinator.", model=mock_model
        )
        task_agent = ChatAgent("You are a planner.", model=mock_model)

        workforce = Workforce(
            description="Test Workforce",
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
            max_refinement_iterations=5,
        )

        assert workforce.max_refinement_iterations == 5

    def test_workforce_max_refinement_iterations_disabled(self, mock_model):
        """Test disabling refinement with max_refinement_iterations=0."""
        coordinator_agent = ChatAgent(
            "You are a coordinator.", model=mock_model
        )
        task_agent = ChatAgent("You are a planner.", model=mock_model)

        workforce = Workforce(
            description="Test Workforce",
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
            max_refinement_iterations=0,
        )

        assert workforce.max_refinement_iterations == 0


class TestValidateAggregatedResult:
    """Tests for the _validate_aggregated_result method."""

    @pytest.mark.asyncio
    async def test_validate_aggregated_result_success(
        self, workforce_with_refinement
    ):
        """Test successful validation of aggregated results."""
        workforce = workforce_with_refinement

        # Create parent task with subtasks
        parent_task = Task(content="Find 5 papers", id="parent_1")
        subtask1 = Task(content="Find paper 1", id="subtask_1.1")
        subtask2 = Task(content="Find paper 2", id="subtask_1.2")
        parent_task.subtasks = [subtask1, subtask2]

        # Mock the task_agent response
        mock_response = MagicMock()
        mock_response.msg = MagicMock()
        mock_response.msg.content = '''```json
{
    "requirements_met": true,
    "unique_count": 5,
    "duplicate_count": 0,
    "missing_count": 0,
    "deduplicated_result": "Paper 1, Paper 2, Paper 3, Paper 4, Paper 5",
    "reasoning": "Found 5 unique papers",
    "additional_task_guidance": null,
    "duplicate_subtask_ids": null
}
```'''

        with patch.object(
            workforce.task_agent, 'step', return_value=mock_response
        ):
            result = workforce._validate_aggregated_result(
                parent_task, "Paper 1, Paper 2, Paper 3, Paper 4, Paper 5"
            )

        assert isinstance(result, ValidationResult)
        assert result.requirements_met is True
        assert result.unique_count == 5

    @pytest.mark.asyncio
    async def test_validate_aggregated_result_with_duplicates(
        self, workforce_with_refinement
    ):
        """Test validation with duplicate detection."""
        workforce = workforce_with_refinement

        parent_task = Task(content="Find 5 papers", id="parent_1")
        subtask1 = Task(content="Find paper 1", id="subtask_1.1")
        subtask2 = Task(content="Find paper 2", id="subtask_1.2")
        subtask3 = Task(content="Find paper 3", id="subtask_1.3")
        parent_task.subtasks = [subtask1, subtask2, subtask3]

        mock_response = MagicMock()
        mock_response.msg = MagicMock()
        mock_response.msg.content = '''```json
{
    "requirements_met": false,
    "unique_count": 3,
    "duplicate_count": 2,
    "missing_count": 2,
    "deduplicated_result": "Paper 1, Paper 2, Paper 3",
    "reasoning": "Found duplicates, need 2 more papers",
    "additional_task_guidance": "Find unique papers excluding Paper 1, 2, 3",
    "duplicate_subtask_ids": ["subtask_1.2", "subtask_1.3"]
}
```'''

        with patch.object(
            workforce.task_agent, 'step', return_value=mock_response
        ):
            result = workforce._validate_aggregated_result(
                parent_task, "Paper 1, Paper 1, Paper 2, Paper 2, Paper 3"
            )

        assert isinstance(result, ValidationResult)
        assert result.requirements_met is False
        assert result.duplicate_count == 2
        assert result.duplicate_subtask_ids is not None

    @pytest.mark.asyncio
    async def test_validate_aggregated_result_fallback_on_error(
        self, workforce_with_refinement
    ):
        """Test fallback behavior when validation fails."""
        workforce = workforce_with_refinement

        parent_task = Task(content="Find 5 papers", id="parent_1")
        parent_task.subtasks = []

        # Mock an error during validation
        with patch.object(
            workforce.task_agent, 'step', side_effect=Exception("Test error")
        ):
            result = workforce._validate_aggregated_result(
                parent_task, "Some content"
            )

        # Should return fallback ValidationResult
        assert isinstance(result, ValidationResult)
        assert result.requirements_met is False


class TestApplyRecoveryStrategyRefine:
    """Tests for applying REFINE recovery strategy."""

    @pytest.mark.asyncio
    async def test_apply_recovery_strategy_refine(
        self, workforce_with_refinement
    ):
        """Test applying REFINE recovery strategy."""
        workforce = workforce_with_refinement
        workforce._running = True
        workforce._channel = MagicMock()
        workforce._assignees = {}

        # Create parent task with subtasks
        parent_task = Task(content="Find 5 papers", id="parent_1")
        subtask1 = Task(content="Find paper 1", id="subtask_1.1")
        subtask1.result = "Paper A"
        subtask1.state = TaskState.DONE
        subtask2 = Task(content="Find paper 2", id="subtask_1.2")
        subtask2.result = "Paper A"  # Duplicate
        subtask2.state = TaskState.DONE
        parent_task.subtasks = [subtask1, subtask2]

        # Create validation result
        validation_result = ValidationResult(
            requirements_met=False,
            unique_count=1,
            duplicate_count=1,
            missing_count=1,
            deduplicated_result="Paper A",
            reasoning="Found duplicate",
            additional_task_guidance="Find different paper",
            duplicate_subtask_ids=["subtask_1.2"],
        )

        parent_task.additional_info = {
            'validation_result': validation_result,
            'refinement_iteration': 0,
        }

        refine_decision = TaskAnalysisResult(
            reasoning="Need to refine",
            recovery_strategy=RecoveryStrategy.REFINE,
        )

        # Mock _post_ready_tasks to avoid actual posting
        workforce._post_ready_tasks = AsyncMock()

        result = await workforce._apply_recovery_strategy(
            parent_task, refine_decision
        )

        assert result is True
        # Check that the duplicate subtask was reset for retry
        assert subtask2.state == TaskState.OPEN
        assert subtask2.result is None


class TestWorkforceCloneWithRefinement:
    """Tests for workforce cloning with refinement parameter."""

    def test_clone_preserves_refinement_iterations(self, mock_model):
        """Test that cloning preserves max_refinement_iterations."""
        coordinator_agent = ChatAgent(
            "You are a coordinator.", model=mock_model
        )
        task_agent = ChatAgent("You are a planner.", model=mock_model)

        original = Workforce(
            description="Original Workforce",
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
            max_refinement_iterations=3,
        )

        cloned = original.clone()

        assert cloned.max_refinement_iterations == 3
