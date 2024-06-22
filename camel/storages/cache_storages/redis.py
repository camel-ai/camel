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

import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis

from camel.storages.cache_storages.base import BaseCacheStorage

logger = logging.getLogger(__name__)


class RedisStorage(BaseCacheStorage):
    r"""A concrete implementation of the :obj:`BaseCacheStorage` using Redis as
    the backend. This is suitable for distributed cache systems that require
    persistence and high availability.
    """

    def __init__(
            self,
            url: str = "redis://localhost:6379",
            **kwargs
    ) -> None:
        r"""Initializes the RedisStorage instance with the provided URL and options.

        Args:
            url (str): The URL for connecting to the Redis server.
            **kwargs: Additional keyword arguments for Redis client configuration.

        Raises:
            ImportError: If the `redis.asyncio` module is not installed.
        """
        try:
            import redis.asyncio as aredis
        except ImportError as exc:
            logger.error(
                "Please install `redis` first. You can install it by "
                "running `pip install redis`."
            )
            raise exc

        self._client: aredis.Redis

        self._create_client(url, **kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self) -> None:
        r"""Closes the Redis client asynchronously."""
        await self.client.close()

    def _create_client(
            self,
            url: str = "redis://localhost:6379",
            **kwargs
    ) -> None:
        r"""Creates the Redis client with the provided URL and options.

        Args:
            url (str): The URL for connecting to the Redis server.
            **kwargs: Additional keyword arguments for Redis client configuration.
        """
        import redis.asyncio as aredis

        self._client = aredis.from_url(url, **kwargs)

    @property
    def client(self) -> Redis:
        r"""Returns the Redis client instance.

        Returns:
            redis.asyncio.Redis: The Redis client instance.
        """
        return self._client

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
        try:
            value = json.dumps(value)
            if expire:
                await self.client.setex(key, expire, value)
            else:
                await self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        r"""Retrieves a cache entry by its key.

        Args:
            key (str): The key for the cache entry.

        Returns:
            Optional[Any]: The value of the cache entry if found, None otherwise.
        """
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache: {e}")
            return None

    async def delete_cache(self, key: str) -> bool:
        r"""Deletes a cache entry by its key.

        Args:
            key (str): The key for the cache entry to be deleted.

        Returns:
            bool: True if the entry was successfully deleted, False otherwise.
        """
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting cache: {e}")
            return False

    async def clear_cache(self) -> bool:
        r"""Removes all entries from the cache storage.

        Returns:
            bool: True if the cache was successfully cleared, False otherwise.
        """
        try:
            await self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
