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
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import torch
from datasets import Dataset as HFDataset
from pydantic import ValidationError
from torch.utils.data import Dataset

from camel.datasets.base import (
    BaseDataset,
    DataPoint,
    GenerativeDataset,
    PyTorchDataset,
    SeedDataset,
    SyntheticDataset,
    convert_hf_to_pytorch,
    convert_synthetic_to_pytorch,
    load_pytorch_dataset,
    save_synthetic_dataset,
)


# ruff: noqa: RUF001
def test_datapoint_creation():
    r"""Test creating a DataPoint with valid data."""
    data = {
        'question': 'What is 2+2?',
        'rationale': 'Addition of two numbers',
        'final_answer': '4',
    }

    datapoint = DataPoint(**data)

    assert datapoint.question == 'What is 2+2?'
    assert datapoint.rationale == 'Addition of two numbers'
    assert datapoint.final_answer == '4'
    assert datapoint.difficulty is None
    assert datapoint.metadata is None


def test_datapoint_validation():
    r"""Test DataPoint validation with missing required fields."""
    with pytest.raises(ValidationError):
        DataPoint(question='What is 2+2?')

    with pytest.raises(ValidationError):
        DataPoint(question='What is 2+2?', rationale='Addition')


def test_datapoint_to_dict():
    r"""Test converting DataPoint to dictionary."""
    data = {
        'question': 'What is 2+2?',
        'rationale': 'Addition of two numbers',
        'final_answer': '4',
        'difficulty': 'easy',
        'metadata': {'topic': 'math'},
    }

    datapoint = DataPoint(**data)
    data_dict = datapoint.to_dict()

    assert data_dict['question'] == 'What is 2+2?'
    assert data_dict['rationale'] == 'Addition of two numbers'
    assert data_dict['final_answer'] == '4'
    assert data_dict['difficulty'] == 'easy'
    assert data_dict['metadata'] == {'topic': 'math'}


def test_datapoint_from_dict():
    r"""Test creating DataPoint from dictionary."""
    data = {
        'question': 'What is 2+2?',
        'rationale': 'Addition of two numbers',
        'final_answer': '4',
    }

    datapoint = DataPoint.from_dict(data)

    assert datapoint.question == 'What is 2+2?'
    assert datapoint.rationale == 'Addition of two numbers'
    assert datapoint.final_answer == '4'


@pytest.fixture
def sample_data():
    r"""Fixture providing sample data for testing."""
    return [
        {
            'question': 'What is 2+2?',
            'rationale': 'Addition of two numbers',
            'final_answer': '4',
        },
        {
            'question': 'What is 3×3?',
            'rationale': 'Multiplication of two numbers',
            'final_answer': '9',
        },
    ]


@pytest.mark.asyncio
async def test_base_dataset_setup(sample_data):
    r"""Test BaseDataset setup process."""
    with tempfile.TemporaryDirectory() as temp_dir:
        dataset = BaseDataset(data=sample_data, cache_dir=temp_dir)
        await dataset.setup()

        assert dataset._is_setup
        assert len(dataset.data) == 2
        assert isinstance(dataset.data[0], DataPoint)
        assert dataset.data[0].question == 'What is 2+2?'
        assert dataset.data[1].final_answer == '9'


@pytest.mark.asyncio
async def test_base_dataset_empty_setup():
    r"""Test BaseDataset setup with empty data."""
    dataset = BaseDataset(data=None)
    await dataset.setup()

    assert dataset._is_setup
    assert len(dataset.data) == 0


@pytest.mark.asyncio
async def test_base_dataset_cleanup():
    r"""Test BaseDataset cleanup process."""
    dataset = BaseDataset(data=[])
    await dataset.setup()
    assert dataset._is_setup

    await dataset.cleanup()
    assert not dataset._is_setup


def test_base_dataset_sample(sample_data):
    r"""Test sampling from BaseDataset."""
    dataset = BaseDataset(data=sample_data)
    dataset._is_setup = True
    dataset.data = [DataPoint(**item) for item in sample_data]

    sample = dataset.sample()
    assert isinstance(sample, DataPoint)
    assert sample in dataset.data


def test_base_dataset_len(sample_data):
    r"""Test BaseDataset length."""
    dataset = BaseDataset(data=sample_data)
    dataset._is_setup = True
    dataset.data = [DataPoint(**item) for item in sample_data]

    assert len(dataset) == 2


def test_base_dataset_getitem(sample_data):
    r"""Test BaseDataset item access."""
    dataset = BaseDataset(data=sample_data)
    dataset._is_setup = True
    dataset.data = [DataPoint(**item) for item in sample_data]

    item = dataset[0]
    assert isinstance(item, DataPoint)
    assert item.question == 'What is 2+2?'

    with pytest.raises(IndexError):
        _ = dataset[100]  # Out of bounds


def test_base_dataset_metadata():
    r"""Test BaseDataset metadata."""
    dataset = BaseDataset(data=[], cache_dir='/tmp', custom_param='value')

    metadata = dataset.metadata
    assert metadata['cache_dir'] == '/tmp'
    assert metadata['custom_param'] == 'value'


def test_seed_dataset_init_from_hf_dataset():
    r"""
    Test SeedDataset initialization from a
    Hugging Face Dataset with various scenarios.
    """

    # **Test 1: Initialization with proper mock data (only required fields)**
    valid_data = [
        {
            "question": "What is 2 + 2?",
            "rationale": "Addition of 2 and 2.",
            "final_answer": "4",
        },
        {
            "question": "Is the sky blue?",
            "rationale": "Observation of clear weather.",
            "final_answer": "yes",
        },
    ]
    hf_valid = HFDataset.from_list(valid_data)

    dataset = SeedDataset(data=hf_valid, min_samples=1, strict=True)

    # Verify the dataset initialized correctly
    assert len(dataset) == 2, "Dataset should contain 2 items."
    assert isinstance(
        dataset[0], DataPoint
    ), "Items should be DataPoint instances."
    assert (
        dataset[0].question == "What is 2 + 2?"
    ), "Question should match input."
    assert (
        dataset[0].rationale == "Addition of 2 and 2."
    ), "Rationale should match input."
    assert dataset[0].final_answer == "4", "Final answer should match input."
    assert (
        dataset[1].question == "Is the sky blue?"
    ), "Second question should match input."
    assert (
        dataset[1].rationale == "Observation of clear weather."
    ), "Second rationale should match input."
    assert (
        dataset[1].final_answer == "yes"
    ), "Second final answer should match input."
    assert (
        dataset[0].difficulty is None
    ), "Difficulty should be None when not provided."
    assert (
        dataset[0].metadata is None
    ), "Metadata should be None when not provided."

    # **Test 2: Initialization with invalid data**
    # Sub-test 2a: Missing required field with strict=True
    invalid_data_missing = [
        {"question": "What is 3 + 3?", "final_answer": "6"}
    ]
    hf_invalid_missing = HFDataset.from_list(invalid_data_missing)
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=hf_invalid_missing, min_samples=1, strict=True)

    # Sub-test 2b: Missing required field with strict=False
    dataset_non_strict = SeedDataset(
        data=hf_invalid_missing, min_samples=0, strict=False
    )
    assert (
        len(dataset_non_strict) == 0
    ), "Invalid items should be filtered out in non-strict mode."

    # Sub-test 2c: Empty dataset with min_samples=1
    hf_empty = HFDataset.from_list([])
    with pytest.raises(
        ValueError,
        match="The dataset does not contain enough samples. Need 1, got 0",
    ):
        SeedDataset(data=hf_empty, min_samples=1, strict=True)

    # Sub-test 2d: Empty dataset with min_samples=0
    dataset_empty = SeedDataset(data=hf_empty, min_samples=0, strict=True)
    assert (
        len(dataset_empty) == 0
    ), "Empty dataset should have zero length when min_samples=0."

    # **Test 3: Initialization with optional fields and additional fields**
    data_with_optional = [
        {
            "question": "What is the capital of France?",
            "rationale": "France is a country in Europe.",
            "final_answer": "Paris",
            "difficulty": "easy",
            "metadata": {"source": "geography", "id": 123},
            "extra_field": "this should be ignored",  # Not in DataPoint
        }
    ]
    hf_optional = HFDataset.from_list(data_with_optional)
    dataset_optional = SeedDataset(
        data=hf_optional, min_samples=1, strict=True
    )

    # Verify the dataset initialized correctly
    assert len(dataset_optional) == 1, "Dataset should contain 1 item."
    assert isinstance(
        dataset_optional[0], DataPoint
    ), "Item should be a DataPoint instance."
    assert (
        dataset_optional[0].question == "What is the capital of France?"
    ), "Question should match."
    assert (
        dataset_optional[0].rationale == "France is a country in Europe."
    ), "Rationale should match."
    assert (
        dataset_optional[0].final_answer == "Paris"
    ), "Final answer should match."
    assert (
        dataset_optional[0].difficulty == "easy"
    ), "Difficulty should be set correctly."
    assert dataset_optional[0].metadata == {
        "source": "geography",
        "id": 123,
    }, "Metadata should match."
    assert (
        "extra_field" not in dataset_optional[0].__dict__
    ), "Extra field should not be present in DataPoint."


def test_seed_dataset_init_from_pytorch_dataset():
    r"""
    Test SeedDataset initialization from a
    PyTorch Dataset with various scenarios.
    """

    class MockPyTorchDataset(Dataset):
        def __init__(self, data_list):
            self.data = data_list

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            return self.data[idx]

    # **Test 1: Initialization with proper mock data (only required fields)**
    valid_data = [
        {
            "question": "What is 2 + 2?",
            "rationale": "Addition of 2 and 2.",
            "final_answer": "4",
        },
        {
            "question": "Is the sky blue?",
            "rationale": "Observation of clear weather.",
            "final_answer": "yes",
        },
    ]
    pytorch_valid = MockPyTorchDataset(valid_data)
    dataset = SeedDataset(data=pytorch_valid, min_samples=1, strict=True)

    assert len(dataset) == 2, "Dataset should contain 2 items."
    assert isinstance(
        dataset[0], DataPoint
    ), "Items should be DataPoint instances."
    assert (
        dataset[0].question == "What is 2 + 2?"
    ), "Question should match input."
    assert (
        dataset[0].rationale == "Addition of 2 and 2."
    ), "Rationale should match input."
    assert dataset[0].final_answer == "4", "Final answer should match input."
    assert (
        dataset[1].question == "Is the sky blue?"
    ), "Second question should match input."
    assert (
        dataset[1].rationale == "Observation of clear weather."
    ), "Second rationale should match input."
    assert (
        dataset[1].final_answer == "yes"
    ), "Second final answer should match input."
    assert (
        dataset[0].difficulty is None
    ), "Difficulty should be None when not provided."
    assert (
        dataset[0].metadata is None
    ), "Metadata should be None when not provided."

    # **Test 2: Initialization with invalid data**
    # Sub-test 2a: Missing required field with strict=True
    invalid_data_missing = [
        {
            "question": "What is 3 + 3?",
            "final_answer": "6",
        }  # Missing rationale
    ]
    pytorch_invalid_missing = MockPyTorchDataset(invalid_data_missing)
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=pytorch_invalid_missing, min_samples=1, strict=True)

    # Sub-test 2b: Missing required field with strict=False
    dataset_non_strict = SeedDataset(
        data=pytorch_invalid_missing, min_samples=0, strict=False
    )
    assert (
        len(dataset_non_strict) == 0
    ), "Invalid items should be filtered out in non-strict mode."

    # Sub-test 2c: Empty dataset with min_samples=1
    pytorch_empty = MockPyTorchDataset([])
    with pytest.raises(
        ValueError,
        match="The dataset does not contain enough samples. Need 1, got 0",
    ):
        SeedDataset(data=pytorch_empty, min_samples=1, strict=True)

    # Sub-test 2d: Empty dataset with min_samples=0
    dataset_empty = SeedDataset(data=pytorch_empty, min_samples=0, strict=True)
    assert (
        len(dataset_empty) == 0
    ), "Empty dataset should have zero length when min_samples=0."

    # **Test 3: Initialization with optional fields and additional fields**
    data_with_optional = [
        {
            "question": "What is the capital of France?",
            "rationale": "France is a country in Europe.",
            "final_answer": "Paris",
            "difficulty": "easy",
            "metadata": {"source": "geography", "id": 123},
            "extra_field": "this should be ignored",  # Not in DataPoint
        }
    ]
    pytorch_optional = MockPyTorchDataset(data_with_optional)
    dataset_optional = SeedDataset(
        data=pytorch_optional, min_samples=1, strict=True
    )

    # Verify the dataset initialized correctly
    assert len(dataset_optional) == 1, "Dataset should contain 1 item."
    assert isinstance(
        dataset_optional[0], DataPoint
    ), "Item should be a DataPoint instance."
    assert (
        dataset_optional[0].question == "What is the capital of France?"
    ), "Question should match."
    assert (
        dataset_optional[0].rationale == "France is a country in Europe."
    ), "Rationale should match."
    assert (
        dataset_optional[0].final_answer == "Paris"
    ), "Final answer should match."
    assert (
        dataset_optional[0].difficulty == "easy"
    ), "Difficulty should be set correctly."
    assert dataset_optional[0].metadata == {
        "source": "geography",
        "id": 123,
    }, "Metadata should match."
    assert (
        "extra_field" not in dataset_optional[0].__dict__
    ), "Extra field should not be present in DataPoint."

    # **Test 4: PyTorch-specific edge cases**
    # Sub-test 4a: Dataset without __len__
    class NoLenDataset(Dataset):
        def __getitem__(self, idx):
            return {
                "question": "Test",
                "rationale": "Test",
                "final_answer": "Test",
            }

    with pytest.raises(TypeError) as excinfo:
        SeedDataset(NoLenDataset(), min_samples=1, strict=True)
    assert "does not implement `__len__()`." in str(excinfo.value)

    # Sub-test 4b: Dataset with non-dict items
    class NonDictDataset(Dataset):
        def __len__(self):
            return 1

        def __getitem__(self, idx):
            return "not a dict"

    with pytest.raises(
        TypeError, match="Item at index 0 is not a dict: got str"
    ):
        SeedDataset(data=NonDictDataset(), min_samples=1, strict=True)


def test_seed_dataset_init_from_json_file():
    r"""
    Test SeedDataset initialization from a JSON file with various scenarios.
    """

    # **Test 1: Initialization with a valid JSON file (only required fields)**
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        valid_data = [
            {
                "question": "What is 2 + 2?",
                "rationale": "Addition of 2 and 2.",
                "final_answer": "4",
            },
            {
                "question": "Is the sky blue?",
                "rationale": "Observation of clear weather.",
                "final_answer": "yes",
            },
        ]
        json.dump(valid_data, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    dataset = SeedDataset(data=tmp_file_path, min_samples=1, strict=True)
    assert len(dataset) == 2, "Dataset should contain 2 items."
    assert isinstance(
        dataset[0], DataPoint
    ), "Items should be DataPoint instances."
    assert (
        dataset[0].question == "What is 2 + 2?"
    ), "Question should match input."
    assert (
        dataset[0].rationale == "Addition of 2 and 2."
    ), "Rationale should match input."
    assert dataset[0].final_answer == "4", "Final answer should match input."
    assert (
        dataset[1].question == "Is the sky blue?"
    ), "Second question should match input."
    assert (
        dataset[1].rationale == "Observation of clear weather."
    ), "Second rationale should match input."
    assert (
        dataset[1].final_answer == "yes"
    ), "Second final answer should match input."
    assert (
        dataset[0].difficulty is None
    ), "Difficulty should be None when not provided."
    assert (
        dataset[0].metadata is None
    ), "Metadata should be None when not provided."

    # **Test 2: Initialization with invalid JSON file (malformed JSON)**
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        tmp_file.write(
            '[{"question": "Test", "rationale": "Test", "final_answer": "Test"'
        )  # Missing closing bracket
        tmp_file_path = Path(tmp_file.name)

    with pytest.raises(ValueError, match="Invalid JSON in file"):
        SeedDataset(data=tmp_file_path, min_samples=1, strict=True)

    # **Test 3: Initialization with JSON file containing non-list data**
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        json.dump(
            {"question": "Test", "rationale": "Test", "final_answer": "Test"},
            tmp_file,
        )
        tmp_file_path = Path(tmp_file.name)

    with pytest.raises(
        ValueError, match="JSON file must contain a list of dictionaries"
    ):
        SeedDataset(data=tmp_file_path, min_samples=1, strict=True)

    # **Test 4: Initialization with JSON file containing non-dict items**
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        invalid_data = [
            {"question": "Test", "rationale": "Test", "final_answer": "Test"},
            "not a dict",
        ]
        json.dump(invalid_data, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    with pytest.raises(
        ValueError, match="Expected a dictionary at index 1, got str"
    ):
        SeedDataset(data=tmp_file_path, min_samples=1, strict=True)

    # **Test 5: Initialization with a missing JSON file**
    missing_file_path = Path("non_existent_file.json")
    with pytest.raises(FileNotFoundError, match="JSON file not found:"):
        SeedDataset(data=missing_file_path, min_samples=1, strict=True)

    # **Test 6: Initialization with an empty JSON file**
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        json.dump([], tmp_file)
        tmp_file_path = Path(tmp_file.name)

    # Sub-test 6a: Empty dataset with min_samples=1
    with pytest.raises(
        ValueError,
        match="The dataset does not contain enough samples. Need 1, got 0",
    ):
        SeedDataset(data=tmp_file_path, min_samples=1, strict=True)

    # Sub-test 6b: Empty dataset with min_samples=0
    dataset_empty = SeedDataset(data=tmp_file_path, min_samples=0, strict=True)
    assert (
        len(dataset_empty) == 0
    ), "Empty dataset should have zero length when min_samples=0."

    # **Test 7: Initialization with optional fields and additional fields**
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        data_with_optional = [
            {
                "question": "What is the capital of France?",
                "rationale": "France is a country in Europe.",
                "final_answer": "Paris",
                "difficulty": "easy",
                "metadata": {"source": "geography", "id": 123},
                "extra_field": "this should be ignored",
            }
        ]
        json.dump(data_with_optional, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    dataset_optional = SeedDataset(
        data=tmp_file_path, min_samples=1, strict=True
    )
    assert len(dataset_optional) == 1, "Dataset should contain 1 item."
    assert isinstance(
        dataset_optional[0], DataPoint
    ), "Item should be a DataPoint instance."
    assert (
        dataset_optional[0].question == "What is the capital of France?"
    ), "Question should match."
    assert (
        dataset_optional[0].rationale == "France is a country in Europe."
    ), "Rationale should match."
    assert (
        dataset_optional[0].final_answer == "Paris"
    ), "Final answer should match."
    assert (
        dataset_optional[0].difficulty == "easy"
    ), "Difficulty should be set correctly."
    assert dataset_optional[0].metadata == {
        "source": "geography",
        "id": 123,
    }, "Metadata should match."
    assert (
        "extra_field" not in dataset_optional[0].__dict__
    ), "Extra field should not be present in DataPoint."

    # **Test 8: JSON-specific edge cases**
    # Sub-test 8a: Invalid data with strict=True
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        invalid_data = [
            {
                "question": "What is 3 + 3?",
                "final_answer": "6",
            }  # Missing rationale
        ]
        json.dump(invalid_data, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=tmp_file_path, min_samples=1, strict=True)

    # Sub-test 8b: Invalid data with strict=False
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as tmp_file:
        invalid_data = [
            {
                "question": "What is 3 + 3?",
                "final_answer": "6",
            }  # Missing rationale
        ]
        json.dump(invalid_data, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    dataset_non_strict = SeedDataset(
        data=tmp_file_path, min_samples=0, strict=False
    )
    assert (
        len(dataset_non_strict) == 0
    ), "Invalid items should be filtered out in non-strict mode."


def test_seed_dataset_init_from_list():
    r"""
    Test SeedDataset initialization from a list of
    dictionaries with various scenarios.
    """

    # **Test 1: Initialization with a valid list (only required fields)**
    valid_data = [
        {
            "question": "What is 2 + 2?",
            "rationale": "Addition of 2 and 2.",
            "final_answer": "4",
        },
        {
            "question": "Is the sky blue?",
            "rationale": "Observation of clear weather.",
            "final_answer": "yes",
        },
    ]
    dataset = SeedDataset(data=valid_data, min_samples=1, strict=True)
    assert len(dataset) == 2, "Dataset should contain 2 items."
    assert isinstance(
        dataset[0], DataPoint
    ), "Items should be DataPoint instances."
    assert (
        dataset[0].question == "What is 2 + 2?"
    ), "Question should match input."
    assert (
        dataset[0].rationale == "Addition of 2 and 2."
    ), "Rationale should match input."
    assert dataset[0].final_answer == "4", "Final answer should match input."
    assert (
        dataset[1].question == "Is the sky blue?"
    ), "Second question should match input."
    assert (
        dataset[1].rationale == "Observation of clear weather."
    ), "Second rationale should match input."
    assert (
        dataset[1].final_answer == "yes"
    ), "Second final answer should match input."
    assert (
        dataset[0].difficulty is None
    ), "Difficulty should be None when not provided."
    assert (
        dataset[0].metadata is None
    ), "Metadata should be None when not provided."

    # **Test 2: Initialization with a list containing non-dictionary items**
    invalid_list_data = [
        {"question": "Test", "rationale": "Test", "final_answer": "Test"},
        "not a dict",
    ]
    with pytest.raises(
        ValueError, match="Expected a dictionary at index 1, got str"
    ):
        SeedDataset(data=invalid_list_data, min_samples=1, strict=True)

    # **Test 3: Initialization with an empty list**
    empty_data = []
    # Sub-test 3a: Empty list with min_samples=1
    with pytest.raises(
        ValueError,
        match="The dataset does not contain enough samples. Need 1, got 0",
    ):
        SeedDataset(data=empty_data, min_samples=1, strict=True)
    # Sub-test 3b: Empty list with min_samples=0
    dataset_empty = SeedDataset(data=empty_data, min_samples=0, strict=True)
    assert (
        len(dataset_empty) == 0
    ), "Empty dataset should have zero length when min_samples=0."

    # **Test 4: Initialization with dictionaries missing required fields**
    # Sub-test 4a: Missing required field with strict=True
    invalid_data_missing = [
        {
            "question": "What is 3 + 3?",
            "final_answer": "6",
        }  # Missing rationale
    ]
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=invalid_data_missing, min_samples=1, strict=True)
    # Sub-test 4b: Missing required field with strict=False
    dataset_non_strict = SeedDataset(
        data=invalid_data_missing, min_samples=0, strict=False
    )
    assert (
        len(dataset_non_strict) == 0
    ), "Invalid items should be filtered out in non-strict mode."

    # **Test 5: Initialization with optional fields and additional fields**
    data_with_optional = [
        {
            "question": "What is the capital of France?",
            "rationale": "France is a country in Europe.",
            "final_answer": "Paris",
            "difficulty": "easy",
            "metadata": {"source": "geography", "id": 123},
            "extra_field": "this should be ignored",
        }
    ]
    dataset_optional = SeedDataset(
        data=data_with_optional, min_samples=1, strict=True
    )
    assert len(dataset_optional) == 1, "Dataset should contain 1 item."
    assert isinstance(
        dataset_optional[0], DataPoint
    ), "Item should be a DataPoint instance."
    assert (
        dataset_optional[0].question == "What is the capital of France?"
    ), "Question should match."
    assert (
        dataset_optional[0].rationale == "France is a country in Europe."
    ), "Rationale should match."
    assert (
        dataset_optional[0].final_answer == "Paris"
    ), "Final answer should match."
    assert (
        dataset_optional[0].difficulty == "easy"
    ), "Difficulty should be set correctly."
    assert dataset_optional[0].metadata == {
        "source": "geography",
        "id": 123,
    }, "Metadata should match."
    assert (
        "extra_field" not in dataset_optional[0].__dict__
    ), "Extra field should not be present in DataPoint."

    # **Test 6: Mixed valid and invalid items with strict=False**
    mixed_data = [
        {
            "question": "Valid question",
            "rationale": "Valid rationale",
            "final_answer": "Valid",
        },
        {
            "question": "Invalid question",
            "final_answer": "Invalid",
        },  # Missing rationale
    ]
    dataset_mixed = SeedDataset(data=mixed_data, min_samples=1, strict=False)
    assert (
        len(dataset_mixed) == 1
    ), "Only valid items should be included in non-strict mode."
    assert (
        dataset_mixed[0].question == "Valid question"
    ), "Only the valid item should be present."


def test_seed_dataset_methods():
    r"""
    Test the __len__, __getitem__, and sample methods
    of SeedDataset with a mock dataset.
    """
    mock_data = [
        {
            "question": "What is 1+1?",
            "rationale": "Basic addition.",
            "final_answer": "2",
        },
        {
            "question": "Is the Earth round?",
            "rationale": "Scientific consensus.",
            "final_answer": "yes",
        },
        {
            "question": "What is the capital of Japan?",
            "rationale": "Geography knowledge.",
            "final_answer": "Tokyo",
        },
        {
            "question": "How many sides does a triangle have?",
            "rationale": "Definition of a triangle.",
            "final_answer": "3",
        },
    ]
    dataset = SeedDataset(data=mock_data, min_samples=1, strict=True)

    assert len(dataset) == 4, "Dataset should have 4 items."
    assert (
        dataset[0].question == "What is 1+1?"
    ), "First item question should match."
    assert (
        dataset[0].rationale == "Basic addition."
    ), "First item rationale should match."
    assert (
        dataset[0].final_answer == "2"
    ), "First item final_answer should match."
    assert (
        dataset[3].question == "How many sides does a triangle have?"
    ), "Last item question should match."
    assert (
        dataset[3].rationale == "Definition of a triangle."
    ), "Last item rationale should match."
    assert (
        dataset[3].final_answer == "3"
    ), "Last item final_answer should match."
    assert isinstance(
        dataset[0], DataPoint
    ), "Item should be a DataPoint instance."

    # Test __getitem__ with out-of-bounds indices
    with pytest.raises(
        IndexError, match="Index -1 out of bounds for dataset of size 4"
    ):
        dataset[-1]
    with pytest.raises(
        IndexError, match="Index 4 out of bounds for dataset of size 4"
    ):
        dataset[4]

    # Test sample from non-empty dataset
    sampled_item = dataset.sample()
    assert (
        sampled_item in dataset.data
    ), "Sampled item should be in the dataset."

    # Test __len__ and sample with empty dataset
    empty_dataset = SeedDataset(data=[], min_samples=0, strict=True)
    assert len(empty_dataset) == 0, "Empty dataset should have length 0."
    with pytest.raises(RuntimeError, match="Dataset is empty, cannot sample."):
        empty_dataset.sample()


def test_synthetic_dataset_init():
    r"""Test SyntheticDataset initialization."""
    dataset = SyntheticDataset()
    assert dataset._raw_data == []
    assert dataset.data == []


def test_synthetic_dataset_add():
    r"""Test adding items to SyntheticDataset."""
    dataset = SyntheticDataset()
    datapoint = DataPoint(
        question='What is 2+2?',
        rationale='Addition of two numbers',
        final_answer='4',
    )

    dataset.add(datapoint)
    assert len(dataset.data) == 1
    assert dataset.data[0] == datapoint


def test_synthetic_dataset_add_batch():
    r"""Test adding batch of items to SyntheticDataset."""
    dataset = SyntheticDataset()
    datapoints = [
        DataPoint(
            question='What is 2+2?',
            rationale='Addition of two numbers',
            final_answer='4',
        ),
        DataPoint(
            question='What is 3×3?',
            rationale='Multiplication of two numbers',
            final_answer='9',
        ),
    ]

    dataset.add_batch(datapoints)
    assert len(dataset.data) == 2
    assert dataset.data == datapoints


def test_synthetic_dataset_filter():
    r"""Test filtering SyntheticDataset."""
    dataset = SyntheticDataset()
    datapoints = [
        DataPoint(
            question='What is 2+2?',
            rationale='Addition of two numbers',
            final_answer='4',
            difficulty='easy',
        ),
        DataPoint(
            question='What is 3×3?',
            rationale='Multiplication of two numbers',
            final_answer='9',
            difficulty='medium',
        ),
    ]
    dataset.add_batch(datapoints)

    # Filter for easy questions
    filtered = dataset.filter(lambda dp: dp.difficulty == 'easy')
    assert len(filtered.data) == 1
    assert filtered.data[0].question == 'What is 2+2?'


def test_pytorch_dataset_init(sample_data):
    r"""Test PyTorchDataset initialization."""
    dataset = PyTorchDataset(sample_data)
    assert len(dataset) == 2
    assert dataset[0]['question'] == 'What is 2+2?'


def test_pytorch_dataset_from_datapoints():
    r"""Test creating PyTorchDataset from DataPoints."""
    datapoints = [
        DataPoint(
            question='What is 2+2?',
            rationale='Addition of two numbers',
            final_answer='4',
        ),
        DataPoint(
            question='What is 3×3?',
            rationale='Multiplication of two numbers',
            final_answer='9',
        ),
    ]

    dataset = PyTorchDataset.from_datapoints(datapoints)
    assert len(dataset) == 2
    assert dataset[0]['question'] == 'What is 2+2?'
    assert dataset[1]['final_answer'] == '9'


def test_pytorch_dataset_transform():
    r"""Test PyTorchDataset with transform function."""
    data = [
        {
            'question': 'What is 2+2?',
            'rationale': 'Addition of two numbers',
            'final_answer': '4',
        }
    ]

    def transform(sample):
        sample['question'] = sample['question'].upper()
        return sample

    dataset = PyTorchDataset(data, transform=transform)
    assert dataset[0]['question'] == 'WHAT IS 2+2?'


def test_pytorch_dataset_collate_fn():
    r"""Test PyTorchDataset collate function."""
    batch = [
        {
            'question': 'What is 2+2?',
            'rationale': 'Addition of two numbers',
            'final_answer': '4',
            'numeric_value': 4,
        },
        {
            'question': 'What is 3×3?',
            'rationale': 'Multiplication of two numbers',
            'final_answer': '9',
            'numeric_value': 9,
        },
    ]

    result = PyTorchDataset.collate_fn(batch)

    # String fields should be lists
    assert isinstance(result['question'], list)
    assert result['question'] == ['What is 2+2?', 'What is 3×3?']

    # Numeric fields should be tensors
    assert isinstance(result['numeric_value'], torch.Tensor)
    assert torch.equal(result['numeric_value'], torch.tensor([4, 9]))


def test_convert_hf_to_pytorch():
    r"""Test converting HuggingFace dataset to PyTorchDataset."""
    hf_data = [
        {
            'q': 'What is 2+2?',
            'r': 'Addition of two numbers',
            'a': '4',
        },
        {
            'q': 'What is 3×3?',
            'r': 'Multiplication of two numbers',
            'a': '9',
        },
    ]

    hf_dataset = HFDataset.from_list(hf_data)

    # Test with column mapping
    column_mapping = {'q': 'question', 'r': 'rationale', 'a': 'final_answer'}
    pytorch_dataset = convert_hf_to_pytorch(
        hf_dataset, column_mapping=column_mapping
    )

    assert len(pytorch_dataset) == 2
    assert pytorch_dataset[0]['question'] == 'What is 2+2?'
    assert pytorch_dataset[1]['final_answer'] == '9'


def test_convert_synthetic_to_pytorch():
    r"""Test converting SyntheticDataset to PyTorchDataset."""
    synthetic_dataset = SyntheticDataset()
    datapoints = [
        DataPoint(
            question='What is 2+2?',
            rationale='Addition of two numbers',
            final_answer='4',
        ),
        DataPoint(
            question='What is 3×3?',
            rationale='Multiplication of two numbers',
            final_answer='9',
        ),
    ]
    synthetic_dataset.add_batch(datapoints)

    pytorch_dataset = convert_synthetic_to_pytorch(synthetic_dataset)

    assert len(pytorch_dataset) == 2
    assert pytorch_dataset[0]['question'] == 'What is 2+2?'
    assert pytorch_dataset[1]['final_answer'] == '9'


def test_save_and_load_pytorch_dataset():
    r"""Test saving and loading PyTorchDataset."""
    with tempfile.NamedTemporaryFile(suffix='.pt') as temp_file:
        # Create and save dataset
        data = [
            {
                'question': 'What is 2+2?',
                'rationale': 'Addition of two numbers',
                'final_answer': '4',
            }
        ]
        dataset = PyTorchDataset(data)
        dataset.save_to_disk(temp_file.name)

        # Load dataset
        loaded_dataset = load_pytorch_dataset(temp_file.name)

        assert len(loaded_dataset) == 1
        assert loaded_dataset[0]['question'] == 'What is 2+2?'


def test_save_synthetic_dataset():
    r"""Test saving SyntheticDataset."""
    with tempfile.NamedTemporaryFile(suffix='.pt') as temp_file:
        # Create and save dataset
        synthetic_dataset = SyntheticDataset()
        datapoint = DataPoint(
            question='What is 2+2?',
            rationale='Addition of two numbers',
            final_answer='4',
        )
        synthetic_dataset.add(datapoint)

        save_synthetic_dataset(synthetic_dataset, temp_file.name)

        # Load dataset
        loaded_dataset = load_pytorch_dataset(temp_file.name)

        assert len(loaded_dataset) == 1
        assert loaded_dataset[0]['question'] == 'What is 2+2?'


@pytest.mark.asyncio
async def test_generative_dataset():
    r"""Test GenerativeDataset with mocked components."""
    mock_seed_dataset = MagicMock(spec=SeedDataset)
    mock_seed_dataset.__len__.return_value = 5
    mock_seed_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )

    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock()
    mock_verifier.verify.return_value = MagicMock(result="Verified Answer")

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

    # Create GenerativeDataset with mocks
    dataset = GenerativeDataset(
        seed_dataset=mock_seed_dataset,
        verifier=mock_verifier,
        agent=mock_agent,
    )

    # Test generate_new method
    await dataset.generate_new(2)

    # Verify interactions
    assert mock_agent.step.call_count >= 2
    assert mock_verifier.verify.await_count >= 2
    assert len(dataset.data) == 2

    # Verify generated data
    assert all(isinstance(dp, DataPoint) for dp in dataset.data)
    assert all(dp.final_answer == "Verified Answer" for dp in dataset.data)
