# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import datetime
import json
from unittest.mock import MagicMock, patch

import pytest
from huggingface_hub import RepositoryNotFoundError

from camel.datahubs.clients.huggingface import HuggingFaceDatasetManager
from camel.datahubs.models import Record

TOKEN = "your_huggingface_token"
DATASET_NAME = (
    f"test-dataset-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
)


@pytest.fixture
def manager():
    return HuggingFaceDatasetManager(token=TOKEN)


def test_create_dataset(manager):
    with patch("huggingface_hub.HfApi.create_repo") as mock_create_repo:
        mock_create_repo.return_value = {"repo_id": f"username/{DATASET_NAME}"}

        dataset_url = manager.create_dataset(
            name=DATASET_NAME, description="Test dataset"
        )
        assert dataset_url == f"https://huggingface.co/datasets/{DATASET_NAME}"

        mock_create_repo.assert_called_once_with(
            name=DATASET_NAME, repo_type="dataset", private=True, token=TOKEN
        )


def test_add_records(manager):
    records = [
        Record(
            id="record-1",
            content={
                "input": "What is AI?",
                "output": "Artificial Intelligence",
            },
            metadata={"method": "SFT"},
        ),
        Record(
            id="record-2",
            content={"input": "Translate 'hello'", "output": "Bonjour"},
            metadata={"method": "GPT"},
        ),
    ]

    with (
        patch("huggingface_hub.HfApi.upload_file") as mock_upload_file,
        patch(
            "huggingface_hub.hf_hub_download",
            side_effect=RepositoryNotFoundError,
        ),
    ):
        manager.add_records(dataset_name=DATASET_NAME, records=records)

        mock_upload_file.assert_called_once()
        call_args = mock_upload_file.call_args[1]
        assert call_args["repo_id"] == DATASET_NAME
        assert call_args["path_in_repo"] == "records/records.json"
        assert call_args["repo_type"] == "dataset"


def test_update_records(manager):
    existing_records = [
        {
            "id": "record-1",
            "content": {
                "input": "What is AI?",
                "output": "Artificial Intelligence",
            },
            "metadata": {"method": "SFT"},
        }
    ]
    new_records = [
        Record(
            id="record-2",
            content={"input": "Translate 'hello'", "output": "Salut"},
            metadata={"method": "Updated GPT"},
        ),
        Record(
            id="record-3",
            content={"input": "What is ML?", "output": "Machine Learning"},
            metadata={"method": "SFT"},
        ),
    ]

    with (
        patch("huggingface_hub.hf_hub_download") as mock_download,
        patch("huggingface_hub.HfApi.upload_file") as mock_upload_file,
    ):
        mock_download.return_value = "/mock/path/records.json"
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(existing_records)
            )

            manager.update_records(
                dataset_name=DATASET_NAME, records=new_records
            )

            mock_upload_file.assert_called_once()
            call_args = mock_upload_file.call_args[1]
            assert call_args["repo_id"] == DATASET_NAME
            assert call_args["path_in_repo"] == "records/records.json"
            assert call_args["repo_type"] == "dataset"


def test_list_records(manager):
    mock_records = [
        {
            "id": "record-1",
            "content": {
                "input": "What is AI?",
                "output": "Artificial Intelligence",
            },
            "metadata": {"method": "SFT"},
        },
        {
            "id": "record-2",
            "content": {"input": "Translate 'hello'", "output": "Salut"},
            "metadata": {"method": "GPT"},
        },
    ]

    with (
        patch("huggingface_hub.hf_hub_download") as mock_download,
        patch("builtins.open", new_callable=MagicMock) as mock_open,
    ):
        mock_download.return_value = "/mock/path/records.json"
        mock_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(mock_records)
        )

        records = manager.list_records(dataset_name=DATASET_NAME)
        assert len(records) == len(mock_records)

        for original, loaded in zip(mock_records, records):
            assert original["id"] == loaded.id
            assert original["content"] == loaded.content
            assert original["metadata"] == loaded.metadata


def test_add_records_error_on_existing_file(manager):
    records = [
        Record(
            id="record-1",
            content={
                "input": "What is AI?",
                "output": "Artificial Intelligence",
            },
            metadata={"method": "SFT"},
        )
    ]

    with patch("huggingface_hub.hf_hub_download") as mock_download:
        mock_download.return_value = "/mock/path/records.json"

        with pytest.raises(
            ValueError, match="Dataset 'records/records.json' already exists"
        ):
            manager.add_records(dataset_name=DATASET_NAME, records=records)
