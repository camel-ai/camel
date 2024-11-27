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
from typing import List

from camel.datahubs.models import Record


class DatasetManager(ABC):
    r"""Abstract base class for dataset managers."""

    @abstractmethod
    def create_dataset(self, name: str, description: str) -> str:
        r"""Creates a new dataset.

        Args:
            name: The name of the dataset.
            description: A description of the dataset.
        """
        pass

    @abstractmethod
    def add_records(self, dataset_name: str, records: List[Record]) -> None:
        r"""Adds records to a dataset.

        Args:
            dataset_name: The name of the dataset.
            records: A list of records to add to the dataset.
        """
        pass

    @abstractmethod
    def update_records(self, dataset_name: str, records: List[Record]) -> None:
        r"""Updates records in a dataset.

        Args:
            dataset_name: The name of the dataset.
            records: A list of records to update in the dataset.
        """
        pass

    @abstractmethod
    def list_records(self, dataset_name: str) -> List[Record]:
        r"""Lists records in a dataset.

        Args:
            dataset_name: The name of the dataset.
        """
        pass
