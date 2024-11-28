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
from abc import ABC, abstractmethod
from typing import List, Optional

from camel.datahubs.models import Record


class DatasetManager(ABC):
    r"""Abstract base class for dataset managers."""

    @abstractmethod
    def create_dataset(self, name: str) -> str:
        r"""Creates a new dataset.

        Args:
            name: The name of the dataset.
        """
        pass

    # New methods for dataset CRUD operations
    @abstractmethod
    def list_datasets(self, username: str, limit: int = 100) -> List[str]:
        r"""Lists all datasets.

        Args:
            username: The username of the user whose datasets to list.
            limit: The maximum number of datasets to return.

        Returns:
            List of dataset names.
        """
        pass

    @abstractmethod
    def delete_dataset(self, dataset_name: str) -> None:
        r"""Deletes a dataset.

        Args:
            dataset_name: The name of the dataset to delete.
        """
        pass

    @abstractmethod
    def add_records(
        self,
        dataset_name: str,
        records: List[Record],
        filepath: Optional[str] = "records/records.json"
    ) -> None:
        r"""Adds records to a dataset.

        Args:
            dataset_name: The name of the dataset.
            records: A list of records to add to the dataset.
            filepath: The path to the file containing the records.
        """
        pass

    @abstractmethod
    def update_records(
        self,
        dataset_name: str,
        records: List[Record],
        filepath: Optional[str] = "records/records.json"
    ) -> None:
        r"""Updates records in a dataset.

        Args:
            dataset_name: The name of the dataset.
            records: A list of records to update in the dataset.
            filepath: The path to the file containing the records.
        """
        pass

    @abstractmethod
    def list_records(
        self,
        dataset_name: str,
        filepath: Optional[str] = "records/records.json"
    ) -> List[Record]:
        r"""Lists records in a dataset.

        Args:
            dataset_name: The name of the dataset.
            filepath: The path to the file containing the records.
        """
        pass

    # New method for record deletion
    @abstractmethod
    def delete_record(
        self,
        dataset_name: str,
        record_id: str,
        filepath: Optional[str] = "records/records.json"
    ) -> None:
        r"""Deletes a record from the dataset.

        Args:
            dataset_name: The name of the dataset.
            record_id: The ID of the record to delete.
            filepath: The path to the file containing the records.
        """
        pass
