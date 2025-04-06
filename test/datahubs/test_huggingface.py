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
import datetime
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from huggingface_hub.errors import EntryNotFoundError

from camel.datahubs.huggingface import HuggingFaceDatasetManager
from camel.datahubs.models import Record

TOKEN = "your_huggingface_token"
DATASET_NAME = (
    f"test-dataset-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
)
REPO_ID = f"username/{DATASET_NAME}"

os.environ["HF_TOKEN"] = TOKEN


@pytest.fixture
def manager():
    return HuggingFaceDatasetManager()


@pytest.mark.skipif(reason="Hugging Face token Unauthorized for url")
def test_create_dataset(manager):
    with patch("huggingface_hub.HfApi.create_repo") as mock_create_repo:
        mock_create_repo.return_value = {"repo_id": REPO_ID}

        dataset_url = manager.create_dataset(name=REPO_ID)
        assert dataset_url == f"https://huggingface.co/datasets/{REPO_ID}"

        mock_create_repo.assert_called_once_with(
            repo_id=REPO_ID, repo_type="dataset", private=False
        )


def test_create_dataset_card():
    manager = HuggingFaceDatasetManager(token="fake-token")
    dataset_name = "user/test-dataset"
    description = "Test dataset"
    license = "MIT"
    version = "0.1.0"
    tags = ["test", "example"]
    authors = ["camel-ai"]
    size_category = "<1MB"
    language = ["en"]
    task_categories = ["other"]
    content = "Additional information about the dataset."

    with patch(
        "camel.datahubs.HuggingFaceDatasetManager._upload_file"
    ) as mock_upload_file:
        mock_upload_file.return_value = None

        manager.create_dataset_card(
            dataset_name=dataset_name,
            description=description,
            license=license,
            version=version,
            tags=tags,
            authors=authors,
            size_category=size_category,
            language=language,
            task_categories=task_categories,
            content=content,
        )

        mock_upload_file.assert_called_once_with(
            file_content="---\nauthors:\n- camel-ai\ndescription: Test dataset"
            "\nlanguage:\n- en\nlicense: MIT\npretty_name: "
            "user/test-dataset\nsize_categories: <1MB\ntags:\n"
            "- test\n- example\ntask_categories:\n- other\n"
            "version: 0.1.0\n\n---\n\n# Additional Information\n"
            "Additional information about the dataset.\n",
            dataset_name=dataset_name,
            filepath="README.md",
            file_type="md",
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
        patch(
            "huggingface_hub.hf_hub_download",
            side_effect=EntryNotFoundError("404 Client Error."),
        ) as mock_download,
        patch("huggingface_hub.HfApi.upload_file") as mock_upload_file,
    ):
        manager.add_records(dataset_name=REPO_ID, records=records)

        mock_download.assert_called_once()
        mock_upload_file.assert_called_once()
        call_args = mock_upload_file.call_args[1]
        assert call_args["repo_id"] == REPO_ID
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
        patch("builtins.open", new_callable=MagicMock) as mock_open,
    ):
        mock_download.return_value = "/mock/path/records.json"

        mock_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(existing_records, ensure_ascii=False)
        )

        manager.update_records(dataset_name=REPO_ID, records=new_records)

        mock_upload_file.assert_called_once()
        call_args = mock_upload_file.call_args[1]
        assert call_args["repo_id"] == REPO_ID
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
            json.dumps(mock_records, ensure_ascii=False)
        )

        records = manager.list_records(dataset_name=REPO_ID)
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

    with (
        patch(
            "huggingface_hub.hf_hub_download",
            side_effect=ValueError(
                "Dataset 'records/records.json' already exists. "
                "Use `update_records` to modify."
            ),
        ) as mock_download,
        patch("huggingface_hub.HfApi.upload_file") as mock_upload_file,
    ):
        mock_download.return_value = "/mock/path/records.json"

        with pytest.raises(
            ValueError,
            match="Dataset 'records/records.json' already exists. "
            "Use `update_records` to modify.",
        ):
            manager.add_records(dataset_name=REPO_ID, records=records)

        mock_upload_file.assert_not_called()


def test_list_datasets(manager):
    with patch("huggingface_hub.HfApi.list_datasets") as mock_list_datasets:
        mock_dataset = MagicMock()
        mock_dataset.id = REPO_ID
        mock_list_datasets.return_value = [mock_dataset]

        datasets = manager.list_datasets(username="username")
        assert datasets == [REPO_ID]

        mock_list_datasets.assert_called_once()


def test_delete_dataset(manager):
    with patch("huggingface_hub.HfApi.delete_repo") as mock_delete_repo:
        manager.delete_dataset(dataset_name=REPO_ID)
        mock_delete_repo.assert_called_once_with(
            repo_id=REPO_ID, repo_type="dataset"
        )


def test_delete_record(manager):
    with (
        patch("huggingface_hub.hf_hub_download") as mock_download,
        patch("huggingface_hub.HfApi.upload_file") as mock_upload_file,
        patch("builtins.open", new_callable=MagicMock) as mock_open,
    ):
        mock_download.return_value = "/mock/path/records.json"

        existing_records = [
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
        mock_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps(
                [record.model_dump() for record in existing_records],
                ensure_ascii=False,
            )
        )

        manager.delete_record(dataset_name=REPO_ID, record_id="record-1")

        mock_upload_file.assert_called_once()
        call_args = mock_upload_file.call_args[1]
        assert call_args["repo_id"] == REPO_ID
        assert call_args["path_in_repo"] == "records/records.json"
        assert call_args["repo_type"] == "dataset"
