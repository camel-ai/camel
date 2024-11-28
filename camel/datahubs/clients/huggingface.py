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
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError

from camel.datahubs.clients.base import DatasetManager
from camel.datahubs.models import Record
from camel.utils import dependencies_required

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HuggingFaceDatasetManager(DatasetManager):
    r"""A dataset manager for Hugging Face datasets. This class provides
    methods to create, add, update, delete, and list records in a dataset on
    the Hugging Face Hub.
    """

    @dependencies_required('huggingface_hub')
    def __init__(self, token: Optional[str]):
        self.token = token or os.getenv("HUGGING_FACE_TOKEN")
        self.api = HfApi(token=self.token)

    def create_dataset(self, name: str, private: bool = True) -> str:
        r"""Creates a new dataset on the Hugging Face Hub.

        Args:
            name (str): The name of the dataset.
            private (bool): Whether the dataset should be private.

        Returns:
            str: The URL of the created dataset.
        """
        try:
            self.api.repo_info(repo_id=name, repo_type="dataset")
        except RepositoryNotFoundError:
            self.api.create_repo(
                repo_id=name,
                repo_type="dataset",
                private=True,
            )

        return f"https://huggingface.co/datasets/{name}"

    def list_datasets(self, username: str, limit: int = 100) -> List[str]:
        r"""Lists all datasets for the current user.

        Args:
            username: The username of the user whose datasets to list.
            limit: The maximum number of datasets to list.

        Returns:
            List[str]: A list of dataset names.
        """
        try:
            return [
                dataset.id
                for dataset in self.api.list_datasets(
                    author=username, limit=limit
                )
            ]
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return []

    def delete_dataset(self, dataset_name: str) -> None:
        r"""Deletes a dataset from the Hugging Face Hub.

        Args:
            dataset_name (str): The name of the dataset to delete.
        """
        try:
            self.api.delete_repo(repo_id=dataset_name, repo_type="dataset")
            logger.info(f"Dataset '{dataset_name}' deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting dataset '{dataset_name}': {e}")
            raise

    def add_records(
        self,
        dataset_name: str,
        records: List[Record],
        filepath: Optional[str] = "records/records.json",
    ) -> None:
        r"""Adds records to a dataset on the Hugging Face Hub.

        Args:
            dataset_name (str): The name of the dataset.
            filepath: The path to the file containing the records.
            records (List[Record]): A list of records to add to the dataset.

        Raises:
            ValueError: If the dataset already has a records file.
        """
        temp_file = f"{dataset_name.replace('/', '_')}_records.json"

        try:
            hf_hub_download(
                repo_id=dataset_name,
                filename=filepath,
                repo_type="dataset",
                token=self.token,
            )
            raise ValueError(
                f"Dataset '{filepath}' already exists. "
                f"Use `update_records` to modify."
            )
        except EntryNotFoundError:
            logger.info(f"Creating new records for dataset '{dataset_name}'.")
        except Exception as e:
            logger.error(e)
            raise

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump([record.model_dump() for record in records], f)

        try:
            self.api.upload_file(
                path_or_fileobj=temp_file,
                path_in_repo=filepath,
                repo_id=dataset_name,
                repo_type="dataset",
            )
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def update_records(
        self,
        dataset_name: str,
        records: List[Record],
        filepath: Optional[str] = "records/records.json",
    ) -> None:
        temp_file = f"{dataset_name.replace('/', '_')}_records.json"
        existing_records = []

        try:
            downloaded_file_path = hf_hub_download(
                repo_id=dataset_name,
                filename=filepath,
                repo_type="dataset",
                token=self.token,
            )
            with open(downloaded_file_path, "r") as f:
                existing_records = json.load(f)
        except Exception as e:
            logger.error(e)
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
                path_in_repo=filepath,
                repo_id=dataset_name,
                repo_type="dataset",
            )
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def delete_record(
        self,
        dataset_name: str,
        record_id: str,
        filepath: Optional[str] = "records/records.json",
    ) -> None:
        r"""Deletes a record from the dataset.

        Args:
            dataset_name (str): The name of the dataset.
            record_id (str): The ID of the record to delete.
            filepath: The path to the file containing the records.
        """
        temp_file = f"{dataset_name.replace('/', '_')}_records.json"
        existing_records = []

        try:
            downloaded_file_path = hf_hub_download(
                repo_id=dataset_name,
                filename=filepath,
                repo_type="dataset",
                token=self.token,
            )
            with open(downloaded_file_path, "r") as f:
                existing_records = json.load(f)
        except Exception:
            raise ValueError(
                f"Dataset '{dataset_name}' does not have an existing file to "
                f"delete records from."
            )

        filtered_records = [
            record for record in existing_records if record["id"] != record_id
        ]

        with open(temp_file, "w") as f:
            json.dump(filtered_records, f)

        try:
            self.api.upload_file(
                path_or_fileobj=temp_file,
                path_in_repo=filepath,
                repo_id=dataset_name,
                repo_type="dataset",
            )
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def list_records(
        self,
        dataset_name: str,
        filepath: Optional[str] = "records/records.json",
    ) -> List[Record]:
        try:
            downloaded_file_path = hf_hub_download(
                repo_id=dataset_name,
                filename=filepath,
                repo_type="dataset",
                token=self.token,
            )

            print(f"{downloaded_file_path=}")

            with open(downloaded_file_path, "r") as f:
                records_data = json.load(f)

            return [Record(**record) for record in records_data]

        except Exception as e:
            logger.error(f"Error downloading or processing records: {e}")
            return []
