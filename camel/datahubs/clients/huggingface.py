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
import json
import logging
import os
from typing import List, Optional

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.errors import RepositoryNotFoundError

from camel.datahubs.clients.base import DatasetManager
from camel.datahubs.models import Record
from camel.utils import dependencies_required

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HuggingFaceDatasetManager(DatasetManager):
    r"""A dataset manager for Hugging Face datasets. This class provides
    methods to create, add, update, and list records in a dataset on the
    Hugging Face Hub.
    """

    @dependencies_required('huggingface_hub')
    def __init__(self, token: Optional[str]):
        self.api = HfApi()
        self.token = token or os.getenv("HUGGING_FACE_TOKEN")

    def create_dataset(self, name: str, description: str) -> str:
        r"""Creates a new dataset on the Hugging Face Hub.

        Args:
            name (str): The name of the dataset.
            description (str): A description of the dataset.

        Returns:
            str: The URL of the created dataset.
        """
        try:
            self.api.repo_info(
                repo_id=name, repo_type="dataset", token=self.token
            )
        except RepositoryNotFoundError:
            self.api.create_repo(
                repo_id=name,
                repo_type="dataset",
                private=True,
                token=self.token,
            )

        return f"https://huggingface.co/datasets/{name}"

    def add_records(self, dataset_name: str, records: List[Record]) -> None:
        r"""Adds records to a dataset on the Hugging Face Hub.

        Args:
            dataset_name (str): The name of the dataset.
            records (List[Record]): A list of records to add to the dataset.

        Raises:
            ValueError: If the dataset already has a records file.
        """
        filename = "records/records.json"
        temp_file = f"{dataset_name.replace('/', '_')}_records.json"

        try:
            hf_hub_download(
                repo_id=dataset_name,
                filename=filename,
                repo_type="dataset",
                token=self.token,
            )
            raise ValueError(
                f"Dataset '{filename}' already exists. "
                f"Use `update_records` to modify."
            )
        except Exception:
            logger.info(
                f"Creating new record file for dataset '{dataset_name}'."
            )

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump([record.model_dump() for record in records], f)

        try:
            self.api.upload_file(
                path_or_fileobj=temp_file,
                path_in_repo=filename,
                repo_id=dataset_name,
                repo_type="dataset",
                token=self.token,
            )
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def update_records(self, dataset_name: str, records: List[Record]) -> None:
        filename = "records/records.json"
        temp_file = f"{dataset_name.replace('/', '_')}_records.json"
        existing_records = []

        try:
            downloaded_file_path = hf_hub_download(
                repo_id=dataset_name,
                filename=filename,
                repo_type="dataset",
                token=self.token,
            )
            with open(downloaded_file_path, "r") as f:
                existing_records = json.load(f)
        except Exception:
            raise ValueError(
                f"Dataset '{dataset_name}' does not have an existing file to "
                f"update. Use `add_records` first."
            )

        new_records = [record.model_dump() for record in records]
        combined_records = {
            rec["id"]: rec for rec in (existing_records + new_records)
        }.values()

        with open(temp_file, "w") as f:
            json.dump(list(combined_records), f)

        try:
            self.api.upload_file(
                path_or_fileobj=temp_file,
                path_in_repo=filename,
                repo_id=dataset_name,
                repo_type="dataset",
                token=self.token,
            )
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def list_records(self, dataset_name: str) -> list[Record]:
        try:
            downloaded_file_path = hf_hub_download(
                repo_id=dataset_name,
                filename="records/records.json",
                repo_type="dataset",
                token=self.token,
            )

            with open(downloaded_file_path, "r") as f:
                records_data = json.load(f)

            return [Record(**record) for record in records_data]

        except Exception as e:
            logger.error(f"Error downloading or processing records: {e}")
            return []
