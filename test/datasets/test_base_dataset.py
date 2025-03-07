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

import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
import torch
from datasets import Dataset as HFDataset
from pydantic import ValidationError

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
    r"""Test SeedDataset initialization with various input types."""
    # Test with list of dictionaries
    dataset = SeedDataset(data=sample_data, min_samples=1)
    assert dataset._raw_data == sample_data, "Raw data should match input list"
    assert len(dataset.data) == 2, "Processed data should have 2 items"
    assert isinstance(
        dataset.data[0], DataPoint
    ), "Items should be DataPoint instances"
    assert (
        dataset.data[0].question == 'What is 2+2?'
    ), "DataPoint content should match input"

    # Test min_samples validation
    with pytest.raises(ValueError) as exc_info:
        SeedDataset(data=sample_data, min_samples=3)
    assert "must have at least 3 samples, got 2" in str(
        exc_info.value
    ), "Should raise ValueError for insufficient samples"

    # Test with empty data and min_samples=0
    dataset_empty = SeedDataset(data=[], min_samples=0)
    assert len(dataset_empty.data) == 0, "Empty dataset should have no items"


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
