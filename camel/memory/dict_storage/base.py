# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseDictStorage(ABC):
    """
    Abstract base class for Dict storage systems. Provides a consistent
    interface for saving, loading, and clearing data records without any loss
    of information.
    """

    @abstractmethod
    def save(self, records: List[Dict[str, Any]]) -> None:
        """
        Saves the given records into the storage system.

        Args:
            records (List[Dict[str, Any]]): A list of dictionaries representing
                records to be saved.
        """
        ...

    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        """
        Loads all records from the storage system.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the
                stored records.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        Clears all records from the storage system.
        """
        ...
