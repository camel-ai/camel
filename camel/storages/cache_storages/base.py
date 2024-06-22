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
from typing import Any, Optional


class BaseCacheStorage(ABC):
    r"""An abstract base class for cache storage systems. Provides a consistent
    interface for setting, getting, deleting, and clearing cache entries with
    optional expiration.

    This class is meant to be inherited by various cache storage implementations,
    including, but not limited to, in-memory caches, distributed caches like
    Redis, and file-based caches.
    """

    @abstractmethod
    async def set_cache(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        r"""Sets a cache entry with an optional expiration time.

        Args:
            key (str): The key for the cache entry.
            value (Any): The value to be stored in the cache.
            expire (Optional[int]): The expiration time in seconds. If None,
                the cache entry does not expire.

        Returns:
            bool: True if the entry was successfully set, False otherwise.
        """
        pass

    @abstractmethod
    async def get_cache(self, key: str) -> Optional[Any]:
        r"""Retrieves a cache entry by its key.

        Args:
            key (str): The key for the cache entry.

        Returns:
            Optional[Any]: The value of the cache entry if found, None otherwise.
        """
        pass

    @abstractmethod
    async def delete_cache(self, key: str) -> bool:
        r"""Deletes a cache entry by its key.

        Args:
            key (str): The key for the cache entry to be deleted.

        Returns:
            bool: True if the entry was successfully deleted, False otherwise.
        """
        pass

    @abstractmethod
    async def clear_cache(self) -> bool:
        r"""Removes all entries from the cache storage.

        Returns:
            bool: True if the cache was successfully cleared, False otherwise.
        """
        pass
