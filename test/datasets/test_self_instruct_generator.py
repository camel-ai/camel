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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from camel.agents import ChatAgent
from camel.datasets import DataPoint, SelfInstructGenerator
from camel.verifiers import BaseVerifier

pytestmark = pytest.mark.heavy_dependency


@pytest.fixture
def mock_verifier():
    r"""Create a mock verifier fixture for testing."""
    verifier = MagicMock(spec=BaseVerifier)
    verifier.required_packages = ["math", "numpy"]
    verifier.verify = AsyncMock()
    return verifier


@pytest.fixture
def mock_datapoint():
    r"""Create a mock datapoint fixture for testing."""
    return DataPoint(
        question="Sample question?",
        rationale="print('Sample code')",
        final_answer="Sample code output",
        metadata={"synthetic": "False"},
    )


@pytest.fixture
def mock_dataset(mock_datapoint):
    r"""Create a mock dataset fixture for testing."""
    dataset = MagicMock()
    dataset.__iter__ = MagicMock(return_value=iter([mock_datapoint]))
    return dataset


@pytest.fixture
def mock_instruction_agent():
    r"""Create a mock instruction agent fixture for testing."""
    agent = MagicMock(spec=ChatAgent)
    response = MagicMock()
    response.msgs = [MagicMock()]
    response.msgs[0].parsed = SelfInstructGenerator.QuestionSchema(
        question="Generated question?"
    )
    agent.step.return_value = response
    return agent


@pytest.fixture
def mock_rationale_agent():
    r"""Create a mock rationale agent fixture for testing."""
    agent = MagicMock(spec=ChatAgent)
    response = MagicMock()
    response.msgs = [MagicMock()]
    response.msgs[0].parsed = SelfInstructGenerator.RationaleSchema(
        code="print('Generated code')"
    )
    agent.step.return_value = response
    return agent


@pytest.fixture
def generator(
    mock_dataset, mock_verifier, mock_instruction_agent, mock_rationale_agent
):
    r"""Create a SelfInstructGenerator instance with mock dependencies."""
    return SelfInstructGenerator(
        seed_dataset=mock_dataset,
        verifier=mock_verifier,
        instruction_agent=mock_instruction_agent,
        rationale_agent=mock_rationale_agent,
        seed=42,
    )


class TestSelfInstructGeneratorInitialization:
    r"""Tests for the initialization of SelfInstructGenerator."""

    def test_init_with_provided_agents(
        self,
        mock_dataset,
        mock_verifier,
        mock_instruction_agent,
        mock_rationale_agent,
    ):
        r"""Test initialization with provided agents."""
        generator = SelfInstructGenerator(
            seed_dataset=mock_dataset,
            verifier=mock_verifier,
            instruction_agent=mock_instruction_agent,
            rationale_agent=mock_rationale_agent,
        )

        assert generator.seed_dataset == mock_dataset
        assert generator.verifier == mock_verifier
        assert generator.instruction_agent == mock_instruction_agent
        assert generator.rationale_agent == mock_rationale_agent
        assert generator.packages == mock_verifier.required_packages
        assert generator.human_instructions == ["Sample question?"]
        assert generator.machine_instructions == []
        assert generator._data == []


class TestFormatSupportBlock:
    r"""Tests for the format_support_block static method."""

    def test_format_support_block_with_rationale(self, mock_datapoint):
        r"""Test format_support_block with a datapoint that has a rationale."""
        result = SelfInstructGenerator.format_support_block(mock_datapoint)

        expected = (
            f"Question:\n{mock_datapoint.question}\n\n"
            "Code:\n"
            "```python\n"
            f"{mock_datapoint.rationale}\n"
            "```"
        )

        assert result == expected

    def test_format_support_block_without_rationale(self):
        r"""Test format_support_block with a datapoint has no rationale."""
        datapoint = DataPoint(
            question="Sample question without rationale?",
            final_answer="Sample answer",
            metadata={"synthetic": "False"},
        )

        result = SelfInstructGenerator.format_support_block(datapoint)

        expected = (
            f"Question:\n{datapoint.question}\n\n"
            "Code:\n"
            "```python\n"
            "\n"
            "```"
        )

        assert result == expected


class TestGenerateNewInstruction:
    r"""Tests for the generate_new_instruction method."""

    def test_generate_new_instruction(self, generator, mock_datapoint):
        r"""Test generate_new_instruction method."""
        # Create sample datapoints
        support_human_dps = [mock_datapoint]
        support_machine_dps = [
            DataPoint(
                question="Machine generated question?",
                rationale="print('Machine code')",
                final_answer="Machine output",
                metadata={"synthetic": "True"},
            )
        ]

        result = generator.generate_new_instruction(
            generator.instruction_agent, support_human_dps, support_machine_dps
        )

        # Check if the agent was called with the correct prompt
        generator.instruction_agent.step.assert_called_once()
        args, kwargs = generator.instruction_agent.step.call_args

        # Verify the prompt contains the examples
        prompt = args[0]
        assert "Sample question?" in prompt
        assert "Machine generated question?" in prompt

        # Verify the response format is correct
        assert kwargs["response_format"] == generator.QuestionSchema

        # Verify the result
        assert result == "Generated question?"


class TestGenerateRationale:
    r"""Tests for the generate_rationale method."""

    def test_generate_rationale_with_agent(self, generator, mock_datapoint):
        r"""Test generate_rationale with a provided agent."""
        question = "Test question?"
        support_human_dps = [mock_datapoint]

        result = generator.generate_rationale(
            question, generator.rationale_agent, support_human_dps
        )

        # Check if the agent was called with the correct prompt
        generator.rationale_agent.step.assert_called_once()
        args, kwargs = generator.rationale_agent.step.call_args

        # Verify the prompt contains the examples and question
        prompt = args[0]
        assert "Sample question?" in prompt
        assert "Test question?" in prompt

        # Verify the response format is correct
        assert kwargs["response_format"] == generator.RationaleSchema

        # Verify the result
        assert result == "print('Generated code')"

    @patch(
        'camel.datasets.self_instruct_generator.SelfInstructGenerator.default_rationale_agent'
    )
    def test_generate_rationale_with_default_agent(
        self, mock_default_agent, generator, mock_datapoint
    ):
        r"""Test generate_rationale with the default agent."""
        # Setup mock default agent
        mock_agent = MagicMock()
        response = MagicMock()
        response.msgs = [MagicMock()]
        response.msgs[0].parsed = SelfInstructGenerator.RationaleSchema(
            code="print('Default agent code')"
        )
        mock_agent.step.return_value = response
        mock_default_agent.return_value = mock_agent

        question = "Test question?"
        support_human_dps = [mock_datapoint]

        result = generator.generate_rationale(
            question, support_human_dps=support_human_dps
        )

        # Verify default agent was created
        mock_default_agent.assert_called_once()

        # Verify the result
        assert result == "print('Default agent code')"


class TestGenerateNew:
    r"""Tests for the generate_new async method."""

    @pytest.mark.asyncio
    async def test_generate_new_success(self, generator, mock_datapoint):
        r"""Test successful generation of new datapoints."""
        # Setup mock verifier response
        verifier_response = MagicMock()
        verifier_response.result = "Verified output"
        generator.verifier.verify.return_value = verifier_response

        # Mock the generate methods
        generator.generate_new_instruction = MagicMock(
            return_value="New question?"
        )
        generator.generate_rationale = MagicMock(
            return_value="print('New code')"
        )

        await generator.generate_new(n=1)

        # Verify generated datapoint
        assert len(generator._data) == 1
        assert generator._data[0].question == "New question?"
        assert generator._data[0].rationale == "print('New code')"
        assert generator._data[0].final_answer == "Verified output"
        assert generator._data[0].metadata["synthetic"] == "True"
        assert generator._data[0].metadata["generator"] == "self_instruct"

    @pytest.mark.asyncio
    async def test_generate_new_verification_failure(self, generator):
        r"""Test handling of verification failures during generation."""
        # Create proper mock responses
        none_response = None
        success_response = MagicMock()
        success_response.result = "Verified output"

        # Setup the verify method to first return None, then return a
        # successful response
        generator.verifier.verify = AsyncMock(
            side_effect=[
                none_response,  # First call returns None (failure)
                success_response,  # Second call returns success
            ]
        )

        # Mock the generate methods
        generator.generate_new_instruction = MagicMock(
            side_effect=["Failed question?", "Successful question?"]
        )
        generator.generate_rationale = MagicMock(
            side_effect=["print('Failed code')", "print('Successful code')"]
        )

        # Clear any existing data
        generator._data = []

        await generator.generate_new(
            n=1, max_retries=3
        )  # Reduce retries for test speed

        # Verify generated datapoint
        assert len(generator._data) == 1
        assert generator._data[0].question == "Successful question?"
        assert generator._data[0].rationale == "print('Successful code')"
        assert generator._data[0].final_answer == "Verified output"

    @pytest.mark.asyncio
    async def test_generate_new_validation_error(self, generator):
        r"""Test handling of validation errors during generation."""
        # Setup mock verifier response
        verifier_response = MagicMock()
        verifier_response.result = "Verified output"
        generator.verifier.verify.return_value = verifier_response

        # Mock the generate methods
        generator.generate_new_instruction = MagicMock(
            side_effect=["Failed question?", "Successful question?"]
        )
        generator.generate_rationale = MagicMock(
            side_effect=["print('Failed code')", "print('Successful code')"]
        )

        # Clear any existing data
        generator._data = []

        # Use a custom DataPoint creation function to simulate validation
        # error then success
        original_datapoint = DataPoint

        datapoint_calls = 0

        def mock_datapoint_factory(*args, **kwargs):
            nonlocal datapoint_calls
            datapoint_calls += 1

            if datapoint_calls == 1:
                # First call - raise validation error
                raise ValidationError.from_exception_data(
                    title="ValidationError",
                    line_errors=[
                        {
                            "type": "string_type",
                            "loc": ("final_answer",),
                            "msg": "Input should be a valid string",
                        }
                    ],
                    model=DataPoint,
                )
            else:
                # Second call - succeed
                return original_datapoint(*args, **kwargs)

        with patch(
            'camel.datasets.self_instruct_generator.DataPoint',
            side_effect=mock_datapoint_factory,
        ):
            await generator.generate_new(
                n=1, max_retries=3
            )  # Reduce retries for test speed

            # Verify generated datapoint
            assert len(generator._data) == 1
            assert generator._data[0].question == "Successful question?"
            assert generator._data[0].rationale == "print('Successful code')"
            assert generator._data[0].final_answer == "Verified output"
