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
from datasets import Dataset as HFDataset
from pydantic import ValidationError
from torch.utils.data import Dataset

from camel.datasets import (
    DataPoint,
    FewShotGenerator,
    StaticDataset,
)
from camel.models.stub_model import StubModel


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
    assert datapoint.metadata is None


def test_datapoint_validation():
    r"""Test DataPoint validation with missing required fields."""
    with pytest.raises(ValidationError):
        DataPoint(question='What is 2+2?')

    datapoint = DataPoint(question='What is 2+2?', final_answer='4')
    assert datapoint.question == 'What is 2+2?'
    assert datapoint.rationale is None
    assert datapoint.final_answer == '4'

    datapoint = DataPoint(
        question='What is 2+2?', rationale='Addition', final_answer='4'
    )
    assert datapoint.question == 'What is 2+2?'
    assert datapoint.rationale == 'Addition'
    assert datapoint.final_answer == '4'


def test_datapoint_to_dict():
    r"""Test converting DataPoint to dictionary."""
    data = {
        'question': 'What is 2+2?',
        'rationale': 'Addition of two numbers',
        'final_answer': '4',
        'metadata': {'topic': 'math'},
    }

    datapoint = DataPoint(**data)
    data_dict = datapoint.to_dict()

    assert data_dict['question'] == 'What is 2+2?'
    assert data_dict['rationale'] == 'Addition of two numbers'
    assert data_dict['final_answer'] == '4'
    assert data_dict['metadata'] == {'topic': 'math'}


def test_datapoint_from_dict():
    r"""Test creating DataPoint from dictionary."""
    # Test with rationale
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


def test_static_dataset_init_from_hf_dataset():
    r"""
    Test StaticDataset initialization from a
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

    dataset = StaticDataset(data=hf_valid, min_samples=1, strict=True)

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
        dataset[0].metadata is None
    ), "Metadata should be None when not provided."

    # **Test 2: Initialization with invalid data**
    # Sub-test 2a: Missing required field with strict=True
    invalid_data_missing = [
        {"question": "What is 3 + 3?", "final_answer": "6"}
    ]
    hf_invalid_missing = HFDataset.from_list(invalid_data_missing)
    with pytest.raises(
        ValueError,
        match="Sample at index 0 has invalid 'rationale': "
        "expected str, got <class 'NoneType'>",
    ):
        StaticDataset(data=hf_invalid_missing, min_samples=1, strict=True)

    # Sub-test 2b: Missing required field with strict=False
    dataset_non_strict = StaticDataset(
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
        StaticDataset(data=hf_empty, min_samples=1, strict=True)

    # Sub-test 2d: Empty dataset with min_samples=0
    dataset_empty = StaticDataset(data=hf_empty, min_samples=0, strict=True)
    assert (
        len(dataset_empty) == 0
    ), "Empty dataset should have zero length when min_samples=0."

    # **Test 3: Initialization with optional fields and additional fields**
    data_with_optional = [
        {
            "question": "What is the capital of France?",
            "rationale": "France is a country in Europe.",
            "final_answer": "Paris",
            "metadata": {"source": "geography", "id": 123},
            "extra_field": "this should be ignored",  # Not in DataPoint
        }
    ]
    hf_optional = HFDataset.from_list(data_with_optional)
    dataset_optional = StaticDataset(
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
    assert dataset_optional[0].metadata == {
        "source": "geography",
        "id": 123,
    }, "Metadata should match."
    assert (
        "extra_field" not in dataset_optional[0].__dict__
    ), "Extra field should not be present in DataPoint."


def test_static_dataset_init_from_pytorch_dataset():
    r"""
    Test StaticDataset initialization from a
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
    dataset = StaticDataset(data=pytorch_valid, min_samples=1, strict=True)

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
    with pytest.raises(
        ValueError,
        match="Sample at index 0 has invalid 'rationale': "
        "expected str, got <class 'NoneType'>",
    ):
        StaticDataset(data=pytorch_invalid_missing, min_samples=1, strict=True)

    # Sub-test 2b: Missing required field with strict=False
    dataset_non_strict = StaticDataset(
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
        StaticDataset(data=pytorch_empty, min_samples=1, strict=True)

    # Sub-test 2d: Empty dataset with min_samples=0
    dataset_empty = StaticDataset(
        data=pytorch_empty, min_samples=0, strict=True
    )
    assert (
        len(dataset_empty) == 0
    ), "Empty dataset should have zero length when min_samples=0."

    # **Test 3: Initialization with optional fields and additional fields**
    data_with_optional = [
        {
            "question": "What is the capital of France?",
            "rationale": "France is a country in Europe.",
            "final_answer": "Paris",
            "metadata": {"source": "geography", "id": 123},
            "extra_field": "this should be ignored",  # Not in DataPoint
        }
    ]
    pytorch_optional = MockPyTorchDataset(data_with_optional)
    dataset_optional = StaticDataset(
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
        StaticDataset(NoLenDataset(), min_samples=1, strict=True)
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
        StaticDataset(data=NonDictDataset(), min_samples=1, strict=True)


def test_static_dataset_init_from_json_file():
    r"""
    Test StaticDataset initialization from a JSON file with various scenarios.
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

    dataset = StaticDataset(data=tmp_file_path, min_samples=1, strict=True)
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
        StaticDataset(data=tmp_file_path, min_samples=1, strict=True)

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
        StaticDataset(data=tmp_file_path, min_samples=1, strict=True)

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
        StaticDataset(data=tmp_file_path, min_samples=1, strict=True)

    # **Test 5: Initialization with a missing JSON file**
    missing_file_path = Path("non_existent_file.json")
    with pytest.raises(FileNotFoundError, match="JSON file not found:"):
        StaticDataset(data=missing_file_path, min_samples=1, strict=True)

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
        StaticDataset(data=tmp_file_path, min_samples=1, strict=True)

    # Sub-test 6b: Empty dataset with min_samples=0
    dataset_empty = StaticDataset(
        data=tmp_file_path, min_samples=0, strict=True
    )
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
                "metadata": {"source": "geography", "id": 123},
                "extra_field": "this should be ignored",
            }
        ]
        json.dump(data_with_optional, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    dataset_optional = StaticDataset(
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

    with pytest.raises(
        ValueError,
        match="Sample at index 0 has invalid 'rationale': "
        "expected str, got <class 'NoneType'>",
    ):
        StaticDataset(data=tmp_file_path, min_samples=1, strict=True)

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

    dataset_non_strict = StaticDataset(
        data=tmp_file_path, min_samples=0, strict=False
    )
    assert (
        len(dataset_non_strict) == 0
    ), "Invalid items should be filtered out in non-strict mode."


def test_static_dataset_init_from_list():
    r"""
    Test StaticDataset initialization from a list of
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
    dataset = StaticDataset(data=valid_data, min_samples=1, strict=True)
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
        StaticDataset(data=invalid_list_data, min_samples=1, strict=True)

    # **Test 3: Initialization with an empty list**
    empty_data = []
    # Sub-test 3a: Empty list with min_samples=1
    with pytest.raises(
        ValueError,
        match="The dataset does not contain enough samples. Need 1, got 0",
    ):
        StaticDataset(data=empty_data, min_samples=1, strict=True)
    # Sub-test 3b: Empty list with min_samples=0
    dataset_empty = StaticDataset(data=empty_data, min_samples=0, strict=True)
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
    with pytest.raises(
        ValueError,
        match="Sample at index 0 has invalid 'rationale': "
        "expected str, got <class 'NoneType'>",
    ):
        StaticDataset(data=invalid_data_missing, min_samples=1, strict=True)
    # Sub-test 4b: Missing required field with strict=False
    dataset_non_strict = StaticDataset(
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
            "metadata": {"source": "geography", "id": 123},
            "extra_field": "this should be ignored",
        }
    ]
    dataset_optional = StaticDataset(
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
    dataset_mixed = StaticDataset(data=mixed_data, min_samples=1, strict=False)
    assert (
        len(dataset_mixed) == 1
    ), "Only valid items should be included in non-strict mode."
    assert (
        dataset_mixed[0].question == "Valid question"
    ), "Only the valid item should be present."


def test_static_dataset_methods():
    r"""
    Test the __len__, __getitem__, and sample methods
    of StaticDataset with a mock dataset.
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
    dataset = StaticDataset(data=mock_data, min_samples=1, strict=True)

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
    empty_dataset = StaticDataset(data=[], min_samples=0, strict=True)
    assert len(empty_dataset) == 0, "Empty dataset should have length 0."
    with pytest.raises(RuntimeError, match="Dataset is empty, cannot sample."):
        empty_dataset.sample()


@pytest.mark.asyncio
async def test_few_shot_generator():
    r"""Test FewShotGenerator with mocked components."""
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
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
                parsed=DataPoint(
                    question='Generated Question',
                    rationale='Generated Rationale',
                    final_answer="final",
                ),
            )
        ]
    )

    # Create FewShotGenerator with mocks
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=StubModel("Stub"),
    )

    dataset.agent = mock_agent

    # Test generate_new method
    await dataset.generate_new(2)

    # Verify interactions
    assert mock_agent.step.call_count >= 2
    assert mock_verifier.verify.await_count >= 2
    assert len(dataset._data) == 2

    # Verify generated data
    assert all(isinstance(dp, DataPoint) for dp in dataset._data)
    assert all(dp.final_answer == "Verified Answer" for dp in dataset._data)


@pytest.mark.asyncio
async def test_generate_new():
    r"""Test FewShotGenerator with mocked components."""
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )

    # Create a mock verifier instead of using a real PythonVerifier
    mock_verifier = MagicMock()

    mock_verifier.verify = AsyncMock()
    mock_verifier.verify.side_effect = [
        MagicMock(result="11"),
        MagicMock(result=None),
        MagicMock(result="15"),
    ]

    mock_agent = MagicMock()
    mock_agent.reset = MagicMock()
    mock_agent.step.return_value = MagicMock(
        msgs=[
            MagicMock(
                parsed=DataPoint(
                    question="Generated Question",
                    rationale="Generated Rationale",
                    final_answer="Generated Answer",
                )
            )
        ]
    )
    mock_agent.step.side_effect = [
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 5 + 6?",
                        rationale="print(5 + 6)",
                        final_answer="11",
                    )
                )
            ]
        ),
        # syntactically incorrect
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 3 + 5?",
                        rationale="print(2 + )",  # Syntax error
                        final_answer="None",  # No valid answer
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
                        final_answer="15",
                    )
                )
            ]
        ),
    ]

    # Create FewShotGenerator with mocks
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=StubModel("Stub"),
    )

    dataset.agent = mock_agent

    new_datapoints = await dataset.generate_new(2)

    assert (
        len(new_datapoints) == 2
    ), "Should generate exactly 2 valid datapoints"
    assert mock_agent.step.call_count == 3, "Should retry past invalid output"

    # Check first correct datapoint (5 + 6 = 11)
    dp1 = new_datapoints[0]
    assert dp1.question == "What is 5 + 6?"
    assert dp1.rationale == "print(5 + 6)"
    assert (
        dp1.final_answer == "11"
    ), "Verifier should output '11' from print(5 + 6)"
    assert dp1.metadata["synthetic"] == "True"

    # Check second correct datapoint (7 + 8 = 15)
    dp2 = new_datapoints[1]
    assert dp2.question == "What is 7 + 8?"
    assert dp2.rationale == "print(7 + 8)"
    assert (
        dp2.final_answer == "15"
    ), "Verifier should output '15' from print(7 + 8)"
    assert dp2.metadata["synthetic"] == "True"

    # Verify that the mock verifier was called the expected number of times
    assert (
        mock_verifier.verify.call_count == 3
    ), "Verifier should be called 3 times"


@pytest.mark.asyncio
async def test_generate_new_with_max_retries():
    r"""Test FewShotGenerator retry mechanism with
    max_retries=2 and a sequence of one correct, three wrong,
    and one correct output, expecting failure."""

    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )

    # Create a mock verifier instead of using a real PythonVerifier
    mock_verifier = MagicMock()

    mock_verifier.verify = AsyncMock()
    mock_verifier.verify.side_effect = [
        MagicMock(result="7"),
        MagicMock(result=None),
        MagicMock(result=None),
        MagicMock(result=None),
        MagicMock(result="23"),
    ]

    # Set up mock agent with specific output sequence
    mock_agent = MagicMock()
    mock_agent.reset.return_value = None  # Ensures it does nothing
    mock_agent.step.side_effect = [
        # Correct
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 3 + 4?",
                        rationale="print(3 + 4)",
                        final_answer="7",
                    )
                )
            ]
        ),
        # Wrong: Syntactically incorrect
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 5 + 6?",
                        rationale="print(5 + )",  # Syntax error
                        final_answer="None",  # No valid answer
                    )
                )
            ]
        ),
        # Wrong: Syntactically incorrect
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 7 + 8?",
                        rationale="print(7 + )",  # Syntax error
                        final_answer="None",
                    )
                )
            ]
        ),
        # Wrong: Syntactically incorrect
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 9 + 10?",
                        rationale="print(9 + )",  # Syntax error
                        final_answer="None",
                    )
                )
            ]
        ),
        # Correct
        MagicMock(
            msgs=[
                MagicMock(
                    parsed=DataPoint(
                        question="What is 11 + 12?",
                        rationale="print(11 + 12)",
                        final_answer="23",
                    )
                )
            ]
        ),
    ]

    model = StubModel("OpenAI")

    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset, verifier=mock_verifier, model=model
    )

    dataset.agent = mock_agent

    # Expect RuntimeError due to insufficient valid
    # datapoints within retry limit
    with pytest.raises(
        RuntimeError,
        match="Failed to generate 2 valid datapoints after 2 retries.",
    ):
        await dataset.generate_new(2, max_retries=2)

    # Verify that the agent was called 3 times before failing
    assert (
        mock_agent.step.call_count == 3
    ), "Should attempt 3 times: correct, wrong, wrong"

    # Verify that the mock verifier was called the expected number of times
    assert (
        mock_verifier.verify.call_count == 3
    ), "Verifier should be called 3 times"


@pytest.mark.asyncio
async def test_few_shot_generator_save_to_jsonl(tmp_path):
    r"""Test FewShotGenerator's save_to_jsonl method with mocked data.

    This test verifies that:
    1. Data can be successfully saved to a JSONL file.
    2. The method handles empty datasets appropriately.
    3. IO errors are caught and raised as expected.

    Args:
        tmp_path: Pytest fixture providing a temporary directory.
    """
    # Mock the seed dataset
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )

    # Mock the verifier
    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock()
    mock_verifier.verify.return_value = MagicMock(result="Verified Answer")

    # Mock the agent
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

    model = StubModel("OpenAI")

    # Create FewShotGenerator with mocks
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=model,
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
            rationale="France is a country in Europe, and its capital "
            "is well-known.",
            final_answer="Paris",
            metadata={"created": "2025-03-12T10:03:00"},
        ),
    ]

    # Test 1: Successful save to JSONL
    file_path = tmp_path / "test_dataset.jsonl"
    dataset.save_to_jsonl(file_path)

    # Verify file exists and content is correct
    assert file_path.exists(), "JSONL file was not created"
    with file_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 4, "Incorrect number of lines in JSONL file"

    # Parse and verify all lines
    for i, (line, expected_dp) in enumerate(zip(lines, dataset._data)):
        parsed_line = json.loads(line)
        assert (
            parsed_line["question"] == expected_dp.question
        ), f"Question mismatch at line {i+1}"
        assert (
            parsed_line["rationale"] == expected_dp.rationale
        ), f"Rationale mismatch at line {i+1}"
        assert (
            parsed_line["final_answer"] == expected_dp.final_answer
        ), f"Final answer mismatch at line {i+1}"
        assert "metadata" in parsed_line, f"Metadata missing at line {i+1}"
        assert (
            parsed_line["metadata"]["created"]
            == expected_dp.metadata["created"]
        ), f"Metadata mismatch at line {i+1}"

    # Test 2: Empty dataset raises ValueError
    dataset._data = []
    with pytest.raises(ValueError, match="Dataset is empty. No data to save."):
        dataset.save_to_jsonl(file_path)

    # Test 3: IO Error handling (simulate by using a directory path)
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
    r"""Test FewShotGenerator's flush method with mocked data.

    This test verifies that:
    1. Data can be successfully flushed to a JSONL file and
       the internal data is cleared.
    2. The method handles empty datasets appropriately.
    3. IO errors are caught and raised as expected.

    Args:
        tmp_path: Pytest fixture providing a temporary directory.
    """
    # Mock the seed dataset
    mock_static_dataset = MagicMock(spec=StaticDataset)
    mock_static_dataset.__len__.return_value = 5
    mock_static_dataset.__getitem__.side_effect = lambda i: DataPoint(
        question=f"Question {i}",
        rationale=f"Rationale {i}",
        final_answer=f"Answer {i}",
    )

    # Mock the verifier
    mock_verifier = MagicMock()
    mock_verifier.verify = AsyncMock()
    mock_verifier.verify.return_value = MagicMock(result="Verified Answer")

    # Mock the agent
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

    model = StubModel("OpenAI")

    # Create FewShotGenerator with mocks
    dataset = FewShotGenerator(
        seed_dataset=mock_static_dataset,
        verifier=mock_verifier,
        model=model,
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
            rationale="France is a country in Europe, "
            "and its capital is well-known.",
            final_answer="Paris",
            metadata={"created": "2025-03-12T10:03:00"},
        ),
    ]

    # **Test 1: Successful flush**
    file_path = tmp_path / "test_dataset.jsonl"
    dataset.flush(file_path)

    # Verify file exists and content is correct
    assert file_path.exists(), "JSONL file was not created"
    with file_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 4, "Incorrect number of lines in JSONL file"

    # Parse and verify all lines
    for i, line in enumerate(lines):
        parsed_line = json.loads(line)
        expected_dp = dataset._data[i] if i < len(dataset._data) else None
        # Since flush clears the data, we can't
        # directly compare with dataset._data
        # Instead, we check against the original data structure we set up
        original_data = [
            {
                "question": "What is 2 + 2?",
                "rationale": "Adding 2 and 2 gives 4.",
                "final_answer": "4",
                "metadata": {"created": "2025-03-12T10:00:00"},
            },
            {
                "question": "What color is the sky?",
                "rationale": "The sky appears blue due to "
                "Rayleigh scattering.",
                "final_answer": "Blue",
                "metadata": {"created": "2025-03-12T10:01:00"},
            },
            {
                "question": "How many sides does a triangle have?",
                "rationale": "A triangle is defined as a "
                "shape with three sides.",
                "final_answer": "3",
                "metadata": {"created": "2025-03-12T10:02:00"},
            },
            {
                "question": "What is the capital of France?",
                "rationale": "France is a country in Europe, "
                "and its capital is well-known.",
                "final_answer": "Paris",
                "metadata": {"created": "2025-03-12T10:03:00"},
            },
        ]
        expected_dp = original_data[i]
        assert (
            parsed_line["question"] == expected_dp["question"]
        ), f"Question mismatch at line {i+1}"
        assert (
            parsed_line["rationale"] == expected_dp["rationale"]
        ), f"Rationale mismatch at line {i+1}"
        assert (
            parsed_line["final_answer"] == expected_dp["final_answer"]
        ), f"Final answer mismatch at line {i+1}"
        assert "metadata" in parsed_line, f"Metadata missing at line {i+1}"
        assert (
            parsed_line["metadata"]["created"]
            == expected_dp["metadata"]["created"]
        ), f"Metadata mismatch at line {i+1}"

    # Verify that internal data is cleared
    assert len(dataset._data) == 0, "Internal data was not cleared after flush"

    # **Test 2: Flush with empty dataset**
    dataset._data = []
    with pytest.raises(ValueError, match="Dataset is empty. No data to save."):
        dataset.flush(file_path)

    # **Test 3: IO Error handling with flush**
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
