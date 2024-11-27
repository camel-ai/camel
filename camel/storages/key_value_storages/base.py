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

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseKeyValueStorage(ABC):
    r"""An abstract base class for key-value storage systems. Provides a
    consistent interface for saving, loading, and clearing data records without
    any loss of information.

    An abstract base class designed to serve as a foundation for various
    key-value storage systems. The class primarily interacts through Python
    dictionaries.

    This class is meant to be inherited by multiple types of key-value storage
    implementations, including, but not limited to, JSON file storage, NoSQL
    databases like MongoDB and Redis, as well as in-memory Python dictionaries.
    """

    @abstractmethod
    def save(self, records: List[Dict[str, Any]]) -> None:
        r"""Saves a batch of records to the key-value storage system.

        Args:
            records (List[Dict[str, Any]]): A list of dictionaries, where each
                dictionary represents a unique record to be stored.
        """
        pass

    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        r"""Loads all stored records from the key-value storage system.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                represents a stored record.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        r"""Removes all records from the key-value storage system."""
        pass
