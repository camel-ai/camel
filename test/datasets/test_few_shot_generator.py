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
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.datasets import DataPoint, FewShotGenerator, StaticDataset
from camel.models.base_model import BaseModelBackend
from camel.models.stub_model import StubModel
from camel.verifiers import BaseVerifier


# Fixture for a valid JSONL file with 4 datapoints
@pytest.fixture
def mock_jsonl_file(tmp_path: Path) -> Path:
    """Creates a temporary JSONL file with four valid datapoints."""
    file_path = tmp_path / "mock_data.jsonl"
    datapoints = [
        {
            "question": "What is 2 + 2?",
            "rationale": "Adding 2 and 2 gives 4.",
            "final_answer": "4",
        },
        {
            "question": "What color is the sky?",
            "rationale": "The sky appears blue due to scattering.",
            "final_answer": "Blue",
        },
        {
            "question": "How many sides does a triangle have?",
            "rationale": "A triangle has three sides.",
            "final_answer": "3",
        },
        {
            "question": "What is the capital of France?",
            "rationale": "France's capital is well-known.",
            "final_answer": "Paris",
        },
    ]
    with file_path.open("w", encoding="utf-8") as f:
        for dp in datapoints:
            json.dump(dp, f)
            f.write("\n")
    return file_path


# Fixture for an invalid JSONL file
@pytest.fixture
def mock_wrong_jsonl_file(tmp_path: Path) -> Path:
    """Creates a temporary JSONL file with invalid data for
    error handling tests."""
    file_path = tmp_path / "mock_wrong_data.jsonl"
    invalid_data = [
        '{"question": "Invalid", "rationale": "Missing final_answer"}',
        '{"question": "Invalid", "final_answer": "Answer"}',
        "Not a JSON object",
    ]
    with file_path.open("w", encoding="utf-8") as f:
        for line in invalid_data:
            f.write(line + "\n")
    return file_path


@pytest.mark.asyncio
async def test_few_shot_generator_init():
    """Test FewShotGenerator initialization."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"x = {i}\nfinal_answer = x * 2\nprint(final_answer)",
        final_answer=str(i * 2),
    )
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"x = {i}\nfinal_answer = x * 2\nprint(final_answer)",
            final_answer=str(i * 2),
        )
        for i in range(5)
    ]

    # Mock model
    mock_model = StubModel("Stub")

    # Initialize the generator
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        model=mock_model,
    )

    # Check basic properties
    assert (
        dataset.seed_dataset is mock_static_dataset
    ), "Seed dataset should be set"
    assert dataset.agent is not None, "Agent should be initialized"
    assert dataset.interpreter is not None, "Interpreter should be initialized"
    assert isinstance(dataset._data, list), "Internal data should be a list"
    assert len(dataset._data) == 0, "Internal data should start empty"
    assert (
        not dataset.interpreter.require_confirm
    ), "Interpreter should not require confirmation"
    assert (
        dataset.interpreter.execution_timeout == 30
    ), "Interpreter timeout should be 30 seconds"

    # Test validation with missing rationale
    datapoints = [
        DataPoint(question="Q1", rationale="R1", final_answer="A1").dict(),
        DataPoint(question="Q2", rationale=None, final_answer="A2").dict(),
        DataPoint(question="Q3", rationale="R3", final_answer="A3").dict(),
    ]
    seed_dataset = StaticDataset(data=datapoints)
    mock_model = StubModel("Stub")

    with pytest.raises(
        RuntimeError, match="Seed Data does not follow Datapoint format"
    ):
        FewShotGenerator(seed_dataset=seed_dataset, model=mock_model)


@pytest.mark.asyncio
async def test_generate_new():
    """Test FewShotGenerator's generate_new with real interpreter."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"x = {i}\nfinal_answer = x * 2\nprint(final_answer)",
        final_answer=str(i * 2),
    )
    mock_static_dataset.sample.side_effect = lambda: DataPoint(
        question="Sample Question",
        rationale="x = 3\nfinal_answer = x * 2\nprint(final_answer)",
        final_answer="6",
    )
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"x = {i}\nfinal_answer = x * 2\nprint(final_answer)",
            final_answer=str(i * 2),
        )
        for i in range(5)
    ]

    # Mock agent with a sequence of outputs
    mock_agent = MagicMock()
    mock_agent.reset = MagicMock()
    mock_agent.step.side_effect = [
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 5 + 6?",
                        rationale="print(5 + 6)",
                        final_answer="",
                    )
                )
            ]
        ),
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 3 + 5?",
                        rationale="print(2 + )",
                        final_answer="",
                    )
                )
            ]
        ),
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 7 + 8?",
                        rationale="print(7 + 8)",
                        final_answer="",
                    )
                )
            ]
        ),
    ]

    # Create FewShotGenerator
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset, model=StubModel("Stub")
    )
    dataset.agent = mock_agent

    # Run generate_new
    await dataset.generate_new(2)

    # Check results
    assert (
        len(dataset._data) == 2
    ), "Should generate exactly 2 valid datapoints"
    assert mock_agent.step.call_count == 3, "Should retry past invalid output"
    assert (
        mock_agent.reset.call_count >= 2
    ), "Agent should reset after each step"

    dp1 = dataset._data[0]
    assert dp1.question == "What is 5 + 6?"
    assert dp1.rationale == "print(5 + 6)"
    assert (
        dp1.final_answer == "11"
    ), "Interpreter should output '11' from print(5 + 6)"

    dp2 = dataset._data[1]
    assert dp2.question == "What is 7 + 8?"
    assert dp2.rationale == "print(7 + 8)"
    assert (
        dp2.final_answer == "15"
    ), "Interpreter should output '15' from print(7 + 8)"


@pytest.mark.asyncio
async def test_generate_new_with_max_retries():
    """Test FewShotGenerator retry mechanism with max_retries=2."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"x = {i}\nfinal_answer = x * 2\nprint(final_answer)",
        final_answer=str(i * 2),
    )
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"x = {i}\nfinal_answer = x * 2\nprint(final_answer)",
            final_answer=str(i * 2),
        )
        for i in range(5)
    ]

    # Mock agent with sequence: correct, three wrong, correct
    mock_agent = MagicMock()
    mock_agent.reset.return_value = None
    mock_agent.step.side_effect = [
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 3 + 4?",
                        rationale="print(3 + 4)",
                        final_answer="",
                    )
                )
            ]
        ),
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 5 + 6?",
                        rationale="print(5 + )",
                        final_answer="",
                    )
                )
            ]
        ),
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 7 + 8?",
                        rationale="print(7 + )",
                        final_answer="",
                    )
                )
            ]
        ),
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 9 + 10?",
                        rationale="print(9 + )",
                        final_answer="",
                    )
                )
            ]
        ),
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 11 + 12?",
                        rationale="print(11 + 12)",
                        final_answer="",
                    )
                )
            ]
        ),
    ]

    # Create FewShotGenerator
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset, model=StubModel("Stub")
    )
    dataset.agent = mock_agent

    # Expect RuntimeError due to max retries
    with pytest.raises(
        RuntimeError,
        match="Failed to generate 2 valid datapoints after 2 retries",
    ):
        await dataset.generate_new(2, max_retries=2)

    assert mock_agent.step.call_count == 3, "Should attempt 3 times"
    assert (
        mock_agent.reset.call_count >= 2
    ), "Agent should reset after each step"
    assert (
        len(dataset._data) == 1
    ), "Only one valid datapoint should be generated"
    dp = dataset._data[0]
    assert dp.question == "What is 3 + 4?"
    assert dp.rationale == "print(3 + 4)"
    assert dp.final_answer == "7"


@pytest.mark.asyncio
async def test_few_shot_generator_save_to_jsonl(tmp_path):
    """Test FewShotGenerator's save_to_jsonl method with mocked data."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"Rationale {i}",
            final_answer=f"Answer {i}",
        )
        for i in range(5)
    ]

    # Mock verifier and agent
    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock(
        return_value=MagicMock(result="Verified Answer")
    )
    mock_agent = MagicMock()
    mock_agent.step.return_value = MagicMock(
        msgs=[
            MagicMock(
                parsed={
                    'question': 'Generated Question',
                    'rationale': 'Generated Rationale',
                }
            )
        ]
    )
    mock_agent.reset = MagicMock()

    # Create FewShotGenerator
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=StubModel("OpenAI"),
    )
    dataset.agent = mock_agent

    # Mock data
    dataset._data = [
        DataPoint(
            question="What is 2 + 2?",
            rationale="Adding 2 and 2 gives 4.",
            final_answer="4",
            metadata={"created": "2025-03-12T10:00:00"},
        ),
        DataPoint(
            question="What color is the sky?",
            rationale="The sky appears blue due to Rayleigh scattering.",
            final_answer="Blue",
            metadata={"created": "2025-03-12T10:01:00"},
        ),
        DataPoint(
            question="How many sides does a triangle have?",
            rationale="A triangle is defined as a shape with three sides.",
            final_answer="3",
            metadata={"created": "2025-03-12T10:02:00"},
        ),
        DataPoint(
            question="What is the capital of France?",
            rationale="France is a country in Europe, and "
            "its capital is well-known.",
            final_answer="Paris",
            metadata={"created": "2025-03-12T10:03:00"},
        ),
    ]

    # Test successful save
    file_path = tmp_path / "test_dataset.jsonl"
    dataset.save_to_jsonl(file_path)
    assert file_path.exists(), "JSONL file was not created"
    with file_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 4, "Incorrect number of lines in JSONL file"

    # Test empty dataset
    dataset._data = []
    with pytest.raises(ValueError, match="Dataset is empty. No data to save."):
        dataset.save_to_jsonl(file_path)

    # Test IO error
    invalid_path = tmp_path / "nonexistent" / "test.jsonl"
    dataset._data = [
        DataPoint(
            question="Test",
            rationale="Test rationale",
            final_answer="Test answer",
        )
    ]
    with pytest.raises(IOError, match="No such file or directory"):
        dataset.save_to_jsonl(invalid_path)


@pytest.mark.asyncio
async def test_few_shot_generator_flush(tmp_path):
    """Test FewShotGenerator's flush method with mocked data."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"Rationale {i}",
            final_answer=f"Answer {i}",
        )
        for i in range(5)
    ]

    # Mock verifier and agent
    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock(
        return_value=MagicMock(result="Verified Answer")
    )
    mock_agent = MagicMock()
    mock_agent.step.return_value = MagicMock(
        msgs=[
            MagicMock(
                parsed={
                    'question': 'Generated Question',
                    'rationale': 'Generated Rationale',
                }
            )
        ]
    )
    mock_agent.reset = MagicMock()

    # Create FewShotGenerator
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=StubModel("OpenAI"),
    )
    dataset.agent = mock_agent

    # Mock data
    dataset._data = [
        DataPoint(
            question="What is 2 + 2?",
            rationale="Adding 2 and 2 gives 4.",
            final_answer="4",
            metadata={"created": "2025-03-12T10:00:00"},
        ),
        DataPoint(
            question="What color is the sky?",
            rationale="The sky appears blue due to Rayleigh scattering.",
            final_answer="Blue",
            metadata={"created": "2025-03-12T10:01:00"},
        ),
        DataPoint(
            question="How many sides does a triangle have?",
            rationale="A triangle is defined as a shape with three sides.",
            final_answer="3",
            metadata={"created": "2025-03-12T10:02:00"},
        ),
        DataPoint(
            question="What is the capital of France?",
            rationale="France is a country in Europe, and its "
            "capital is well-known.",
            final_answer="Paris",
            metadata={"created": "2025-03-12T10:03:00"},
        ),
    ]

    # Test successful flush
    file_path = tmp_path / "test_dataset.jsonl"
    dataset.flush(file_path)
    assert file_path.exists(), "JSONL file was not created"
    assert len(dataset._data) == 0, "Internal data was not cleared after flush"

    # Test empty dataset
    dataset._data = []
    with pytest.raises(ValueError, match="Dataset is empty. No data to save."):
        dataset.flush(file_path)

    # Test IO error
    invalid_path = tmp_path / "nonexistent" / "test.jsonl"
    dataset._data = [
        DataPoint(
            question="Test",
            rationale="Test rationale",
            final_answer="Test answer",
        )
    ]
    with pytest.raises(IOError, match="No such file or directory"):
        dataset.flush(invalid_path)


@pytest.mark.asyncio
async def test_few_shot_generator_async(
    mock_jsonl_file: Path, mock_wrong_jsonl_file: Path
):
    """Test FewShotGenerator in an asynchronous context."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"Rationale {i}",
            final_answer=f"Answer {i}",
        )
        for i in range(5)
    ]

    mock_verifier = MagicMock(spec=BaseVerifier)
    mock_model = MagicMock(spec=BaseModelBackend)
    mock_model.model_type = "mock_model_type"

    # Test initialization
    generator = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=mock_model,
        data_path=mock_jsonl_file,
    )
    assert len(generator._data) == 4, "Expected 4 datapoints loaded from JSONL"

    # Test async sampling
    sampled_dp = await generator.async_sample()
    assert isinstance(
        sampled_dp, DataPoint
    ), "Sampled item should be a DataPoint"
    assert (
        len(generator._data) == 3
    ), "Async sampling should reduce datapoints by 1"

    # Test invalid JSONL
    with pytest.raises(ValueError):
        FewShotGenerator(
            seed_dataset=mock_static_dataset,
            verifier=mock_verifier,
            model=mock_model,
            data_path=mock_wrong_jsonl_file,
        )


def test_few_shot_generator_sync(
    mock_jsonl_file: Path, mock_wrong_jsonl_file: Path
):
    """Test FewShotGenerator in a synchronous context."""
    # Mock seed dataset with data attribute
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.data = [
        DataPoint(
            question=f"Question {i}",
            rationale=f"Rationale {i}",
            final_answer=f"Answer {i}",
        )
        for i in range(5)
    ]

    mock_verifier = MagicMock(spec=BaseVerifier)
    mock_model = MagicMock(spec=BaseModelBackend)
    mock_model.model_type = "mock_model_type"

    # Test initialization
    generator = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=mock_model,
        data_path=mock_jsonl_file,
    )
    assert len(generator._data) == 4, "Expected 4 datapoints loaded from JSONL"

    # Test sampling
    sampled_dp = generator.sample()
    assert isinstance(
        sampled_dp, DataPoint
    ), "Sampled item should be a DataPoint"
    assert len(generator._data) == 3, "Sampling should reduce datapoints by 1"

    # Test invalid JSONL
    with pytest.raises(ValueError):
        FewShotGenerator(
            seed_dataset=mock_static_dataset,
            verifier=mock_verifier,
            model=mock_model,
            data_path=mock_wrong_jsonl_file,
        )
