# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class CacheRecord:
    r"""Represents a cached query-response pair with metadata.

    Attributes:
        query (str): The original query text.
        response (str): The cached response for the query.
        query_id (str): Unique identifier for this cache entry.
        created_at (datetime): Timestamp when the entry was created.
        metadata (Dict[str, Any]): Additional metadata about the cache entry.
    """

    query: str
    response: str
    query_id: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseCache(ABC):
    r"""An abstract base class for cache systems.

    This class defines the interface for caching mechanisms that can store
    and retrieve query-response pairs. Implementations may use various
    strategies including exact match, semantic similarity, or hybrid.
    """

    @abstractmethod
    def get(self, query: str) -> Optional[str]:
        r"""Retrieve a cached response for the given query.

        Args:
            query (str): The query to look up in the cache.

        Returns:
            Optional[str]: The cached response if found, None otherwise.
        """
        pass

    @abstractmethod
    def set(self, query: str, response: str, **kwargs: Any) -> Optional[str]:
        r"""Store a query-response pair in the cache.

        Args:
            query (str): The query text.
            response (str): The response to cache.
            **kwargs (Any): Additional arguments for the cache entry.

        Returns:
            Optional[str]: The unique ID of the cache entry, or None.
        """
        pass

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        r"""Delete a specific cache entry by its ID.

        Args:
            entry_id (str): The unique ID of the entry to delete.

        Returns:
            bool: True if the entry was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        r"""Remove all entries from the cache."""
        pass

    @property
    @abstractmethod
    def size(self) -> int:
        r"""Returns the number of entries in the cache.

        Returns:
            int: The number of cached entries.
        """
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        r"""Returns whether the cache is enabled.

        Returns:
            bool: True if cache is enabled, False otherwise.
        """
        pass

    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool) -> None:
        r"""Enable or disable the cache.

        Args:
            value (bool): True to enable, False to disable.
        """
        pass
