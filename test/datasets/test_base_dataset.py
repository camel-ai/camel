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


def test_seed_dataset_init(sample_data):
    r"""Test SeedDataset initialization with valid input data."""
    dataset = SeedDataset(data=sample_data, min_samples=1)
    assert dataset._raw_data == sample_data, "Raw data should match input list"
    assert len(dataset.data) == 2, "Processed data should have 2 items"
    assert isinstance(
        dataset.data[0], DataPoint
    ), "Items should be DataPoint instances"
    assert (
        dataset.data[0].question == 'What is 2+2?'
    ), "DataPoint content should match input"
    with pytest.raises(ValueError) as exc_info:
        SeedDataset(data=sample_data, min_samples=3)
    assert "must have at least 3 samples" in str(
        exc_info.value
    ), "Should raise ValueError for insufficient samples"

    # Test with an empty dataset when min_samples is 0
    dataset_empty = SeedDataset(data=[], min_samples=0)
    assert len(dataset_empty.data) == 0, "Empty dataset should have no items"


def test_seed_dataset_strict_mode():
    r"""Test SeedDataset in strict mode where 
    invalid datapoints raise errors."""
    invalid_data = [
        {
            "question": "Incomplete sample",
            "rationale": "Some reasoning",
        }  # Missing 'final_answer'
    ]
    with pytest.raises(ValueError) as exc_info:
        # strict=True should raise an error on the first invalid datapoint
        SeedDataset(data=invalid_data, min_samples=1, strict=True)
    assert "validation error" in str(
        exc_info.value
    ), "Strict mode should raise ValueError for invalid datapoint"


def test_seed_dataset_non_strict_mode():
    r"""Test SeedDataset in non-strict mode where 
    invalid datapoints are skipped."""

    invalid_data = [
        {"question": "Incomplete sample", "rationale": "Some reasoning"}
    ]
    # strict=False should filter out invalid samples
    dataset = SeedDataset(data=invalid_data, min_samples=0, strict=False)
    # Expect that the invalid sample is skipped, so 
    # dataset.data should be empty
    assert (
        len(dataset.data) == 0
    ), "Non-strict mode should filter out invalid samples"


def test_seed_dataset_init_hf_dataset():
    r"""Test SeedDataset initialization with a fake IMDB-style Hugging Face Dataset."""
    # Mock IMDB-style data
    mock_imdb_data = [
        {
            "text": "This movie was absolutely fantastic, a real joy to watch!",
            "label": 1,
            "rationale": "The reviewer uses positive adjectives like 'fantastic' and 'joy'.",
        },
        {
            "text": "Terrible acting and a boring plot ruined this film.",
            "label": 0,
            "rationale": "Negative terms like 'terrible' and 'boring' suggest dissatisfaction.",
        },
        {
            "text": "An incredible cast made this a thrilling experience.",
            "label": 1,
            "rationale": "Words like 'incredible' and 'thrilling' reflect a positive reaction.",
        },
    ]

    hf_dataset = HFDataset.from_list(mock_imdb_data)

    mapped_dataset = hf_dataset.map(
        lambda example: {
            "question": "What is the sentiment of this review? " f"{example['text'][:30]}...",
            "rationale": example["rationale"],
            "final_answer": "positive" if example["label"] == 1 else "negative",
        }
    )

    # Valid data
    dataset = SeedDataset(data=mapped_dataset, min_samples=1, strict=True)
    assert len(dataset.data) == 3, "There should be 3 valid data points."
    assert isinstance(dataset.data[0], DataPoint), "Items should be DataPoint instances."
    assert dataset.data[0].question == mapped_dataset[0]["question"], "Question should match input."
    assert dataset.data[0].rationale == mapped_dataset[0]["rationale"], "Rationale should match input."
    assert dataset.data[0].final_answer == mapped_dataset[0]["final_answer"], "Final answer should match input."

    # Invalid data
    invalid_data_missing = [
        {
            "question": "What is the sentiment of this review? Missing rationale...",
            "final_answer": "positive",
            # Missing "rationale"
        }
    ]
    hf_invalid_missing = HFDataset.from_list(invalid_data_missing)
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=hf_invalid_missing, min_samples=1, strict=True)

    empty_data = []
    hf_empty = HFDataset.from_list(empty_data)
    with pytest.raises(ValueError, match="Dataset must have at least 1 samples, got 0"):
        SeedDataset(data=hf_empty, min_samples=1, strict=True)

    dataset_empty = SeedDataset(data=hf_empty, min_samples=0, strict=True)
    assert len(dataset_empty.data) == 0, "Empty dataset should have no valid items."

    non_dict_data = [
        "Not a dictionary",
        {
            "question": "Valid question",
            "rationale": "Valid rationale",
            "final_answer": "positive",
        },
    ]
    with pytest.raises(TypeError, match="Unsupported data type"):
        SeedDataset(data=non_dict_data, min_samples=1, strict=True)

    data_with_optional = [
        {
            "question": "What is the sentiment of this review? This movie was awesome!...",
            "rationale": "Positive sentiment detected.",
            "final_answer": "positive",
            "difficulty": "medium",
            "metadata": {"source": "imdb"},
        }
    ]
    hf_optional = HFDataset.from_list(data_with_optional)
    dataset_optional = SeedDataset(data=hf_optional, min_samples=1, strict=True)
    assert dataset_optional.data[0].difficulty == "medium", "Difficulty field should be 'medium'."
    assert dataset_optional.data[0].metadata == {"source": "imdb"}, "Metadata should match input."



def test_seed_dataset_init_pytorch_dataset():
    r"""Test SeedDataset initialization with a
    mock IMDB-style PyTorch Dataset."""

    # Define a reusable PyTorch Dataset class
    class MockIMDBDataset(Dataset):
        def __init__(self, data_list):
            self.data = data_list

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            return self.data[idx]

    valid_data = [
        {
            "text": "This movie was absolutely fantastic, "
            "a real joy to watch!",
            "label": 1,
            "rationale": "The reviewer uses positive adjectives like "
            "'fantastic' and 'joy'.",
        },
        {
            "text": "Terrible acting and a boring plot ruined this film.",
            "label": 0,
            "rationale": "Negative terms like 'terrible' and 'boring' "
            "suggest dissatisfaction.",
        },
        {
            "text": "An incredible cast made this a thrilling experience.",
            "label": 1,
            "rationale": "Words like 'incredible' and 'thrilling' "
            "reflect a positive reaction.",
        },
    ]

    mapped_data = [
        {
            "question": "What is the sentiment of this review? "
            f"{item['text'][:30]}...",
            "rationale": item["rationale"],
            "final_answer": "positive" if item["label"] == 1 else "negative",
        }
        for item in valid_data
    ]

    pytorch_dataset = MockIMDBDataset(mapped_data)
    dataset = SeedDataset(data=pytorch_dataset, min_samples=1)
    assert len(dataset.data) == 3
    assert isinstance(dataset.data[0], DataPoint)
    assert dataset.data[0].question == mapped_data[0]["question"]
    assert dataset.data[0].rationale == mapped_data[0]["rationale"]
    assert dataset.data[0].final_answer == mapped_data[0]["final_answer"]

    invalid_data_missing = [
        {
            "question": "What is the sentiment of this review? "
            "Missing rationale...",
            "final_answer": "positive",
            # Missing "rationale"
        }
    ]
    pytorch_invalid_missing = MockIMDBDataset(invalid_data_missing)
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=pytorch_invalid_missing, min_samples=1)

    empty_data = []
    pytorch_empty = MockIMDBDataset(empty_data)
    with pytest.raises(
        ValueError, match="Dataset must have at least 1 samples, got 0"
    ):
        SeedDataset(data=pytorch_empty, min_samples=1)

    dataset_empty = SeedDataset(data=pytorch_empty, min_samples=0)
    assert len(dataset_empty.data) == 0

    non_dict_data = [
        "Not a dictionary",
        {
            "question": "Valid question",
            "rationale": "Valid rationale",
            "final_answer": "positive",
        },
    ]
    pytorch_non_dict = MockIMDBDataset(non_dict_data)
    with pytest.raises(TypeError, match="Unsupported data type"):
        SeedDataset(data=pytorch_non_dict, min_samples=1)

    data_with_optional = [
        {
            "question": "What is the sentiment of this review? "
            "This movie was awesome!...",
            "rationale": "Positive sentiment detected.",
            "final_answer": "positive",
            "difficulty": "medium",
            "metadata": {"source": "imdb"},
        }
    ]
    pytorch_optional = MockIMDBDataset(data_with_optional)
    dataset_optional = SeedDataset(data=pytorch_optional, min_samples=1)
    assert dataset_optional.data[0].difficulty == "medium"
    assert dataset_optional.data[0].metadata == {"source": "imdb"}


def test_seed_dataset_init_list_extended(sample_data):
    r"""Test SeedDataset initialization with a list of dictionaries."""

    data_with_optional = [
        *sample_data,
        {
            "question": "What is 5-3?",
            "rationale": "Subtraction",
            "final_answer": "2",
            "difficulty": "easy",  # Optional field
            "metadata": {"topic": "math"},  # Optional field
        },
    ]
    dataset = SeedDataset(data=data_with_optional, min_samples=1)
    assert len(dataset.data) == 3, "Dataset should contain 3 items"
    assert (
        dataset.data[2].difficulty == "easy"
    ), "Optional difficulty field should be preserved"
    assert dataset.data[2].metadata == {
        "topic": "math"
    }, "Optional metadata field should be preserved"
    assert (
        dataset.data[0].question == sample_data[0]["question"]
    ), "First item question should match"
    assert (
        dataset.data[1].final_answer == sample_data[1]["final_answer"]
    ), "Second item final_answer should match"

    invalid_data_missing = [
        {"question": "What is 2+2?", "rationale": "Addition"}
    ]
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=invalid_data_missing, min_samples=1)

    invalid_data_type = [
        {
            "question": "What is 3+3?",
            "rationale": "Addition",
            "final_answer": 6,
        }
    ]
    with pytest.raises(ValueError, match="Sample at index 0 validation error"):
        SeedDataset(data=invalid_data_type, min_samples=1)

    empty_data = []
    with pytest.raises(
        ValueError, match="Dataset must have at least 1 samples, got 0"
    ):
        SeedDataset(data=empty_data, min_samples=1)

    dataset_empty = SeedDataset(data=empty_data, min_samples=0)
    assert (
        len(dataset_empty.data) == 0
    ), "Empty dataset with min_samples=0 should have no items"

    non_dict_data = [
        "Not a dictionary",
        {
            "question": "What is 4+4?",
            "rationale": "Addition",
            "final_answer": "8",
        },
    ]
    with pytest.raises(TypeError, match="Unsupported data type"):
        SeedDataset(data=non_dict_data, min_samples=1)

    mixed_data = [
        {
            "question": "What is 1+1?",
            "rationale": "Addition",
            "final_answer": "2",
        },
        {"question": "What is 2+2?"},
    ]
    with pytest.raises(ValueError, match="Sample at index 1 validation error"):
        SeedDataset(data=mixed_data, min_samples=1)


def test_seed_dataset_init_json_file():
    r"""Test SeedDataset initialization with a JSON file path."""

    sample_data = [
        {
            "question": "What is 2+2?",
            "rationale": "Addition",
            "final_answer": "4",
        },
        {
            "question": "What is 3×3?",
            "rationale": "Multiplication",
            "final_answer": "9",
        },
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump(sample_data, temp_file)
        temp_file.flush()
        dataset = SeedDataset(data=temp_file.name, min_samples=1)
        assert len(dataset.data) == 2, "Should have 2 items from the JSON file"
        assert isinstance(
            dataset.data[0], DataPoint
        ), "Items should be DataPoint instances"
        assert (
            dataset.data[0].question == "What is 2+2?"
        ), "Question should match the JSON data"
        assert (
            dataset.data[1].final_answer == "9"
        ), "Final answer should match the JSON data"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as invalid_file:
        invalid_file.write("Invalid JSON")
        invalid_file.flush()
        with pytest.raises(json.JSONDecodeError):
            SeedDataset(data=invalid_file.name, min_samples=1)

    invalid_data_missing = [
        {
            "question": "What is 2+2?",
            "rationale": "Addition",  # Missing "final_answer"
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump(invalid_data_missing, temp_file)
        temp_file.flush()
        with pytest.raises(
            ValueError, match="Sample at index 0 validation error"
        ):
            SeedDataset(data=temp_file.name, min_samples=1)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump([], temp_file)
        temp_file.flush()
        with pytest.raises(
            ValueError, match="Dataset must have at least 1 samples, got 0"
        ):
            SeedDataset(data=temp_file.name, min_samples=1)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump([], temp_file)
        temp_file.flush()
        dataset_empty = SeedDataset(data=temp_file.name, min_samples=0)
        assert (
            len(dataset_empty.data) == 0
        ), "Empty dataset with min_samples=0 should have no items"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump({"not": "a list"}, temp_file)
        temp_file.flush()
        with pytest.raises(
            ValueError, match="JSON file must contain a list of dictionaries"
        ):
            SeedDataset(data=temp_file.name, min_samples=1)

    data_with_optional = [
        {
            "question": "What is 5-3?",
            "rationale": "Subtraction",
            "final_answer": "2",
            "difficulty": "easy",
            "metadata": {"topic": "math"},
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump(data_with_optional, temp_file)
        temp_file.flush()
        dataset_optional = SeedDataset(data=temp_file.name, min_samples=1)
        assert (
            dataset_optional.data[0].difficulty == "easy"
        ), "Optional difficulty field should be preserved"
        assert dataset_optional.data[0].metadata == {
            "topic": "math"
        }, "Optional metadata field should be preserved"

    data_with_extra = [
        {
            "question": "What is 4+4?",
            "rationale": "Addition",
            "final_answer": "8",
            "extra_field": "should be ignored",
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temp_file:
        json.dump(data_with_extra, temp_file)
        temp_file.flush()
        dataset_extra = SeedDataset(data=temp_file.name, min_samples=1)
        assert (
            "extra_field" not in dataset_extra.data[0].__dict__
        ), "Extra fields should be ignored"


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
