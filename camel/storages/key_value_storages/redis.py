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
from typing import TYPE_CHECKING, Any, Optional, List, Dict


from camel.storages.key_value_storages import BaseKeyValueStorage

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisStorage(BaseKeyValueStorage):
    r"""A concrete implementation of the :obj:`BaseCacheStorage` using Redis as
    the backend. This is suitable for distributed cache systems that require
    persistence and high availability.
    """

    def __init__(
            self,
            sid: str,
            url: str = "redis://localhost:6379",
            **kwargs
    ) -> None:
        r"""Initializes the RedisStorage instance with the provided URL and options.

        Args:
            sid (str): The ID for the storage instance to identify the record space.
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

        self._client: Optional[aredis.Redis] = None
        self._url = url
        self._sid = sid

        self._create_client(**kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self) -> None:
        r"""Closes the Redis client asynchronously."""
        await self.client.close()

    def _create_client(
            self,
            **kwargs
    ) -> None:
        r"""Creates the Redis client with the provided URL and options.

        Args:
            **kwargs: Additional keyword arguments for Redis client configuration.
        """
        import redis.asyncio as aredis

        self._client = aredis.from_url(self._url, **kwargs)

    @property
    def client(self) -> "Redis":
        r"""Returns the Redis client instance.

        Returns:
            redis.asyncio.Redis: The Redis client instance.
        """
        return self._client

    async def save(self, records: List[Dict[str, Any]], expire: Optional[int] = None) -> None:
        r"""Saves a batch of records to the key-value storage system.

        Args:
            records (List[Dict[str, Any]]): A list of dictionaries, where each
                dictionary represents a unique record to be stored.
            expire (Optional[int]): The expiration time in seconds. If None,
                the cache entry does not expire.
        """
        try:
            value = json.dumps(records)
            if expire:
                await self.client.setex(self._sid, expire, value)
            else:
                await self.client.set(self._sid, value)
        except Exception as e:
            logger.error(f"Error saving records: {e}")

    async def load(self) -> List[Dict[str, Any]]:
        r"""Loads all stored records from the key-value storage system.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                represents a stored record.
        """
        try:
            value = await self.client.get(self._sid)
            if value:
                return json.loads(value)
            return []
        except Exception as e:
            logger.error(f"Error loading records: {e}")
            return []

    async def clear(self) -> None:
        r"""Removes all records from the key-value storage system."""
        try:
            await self.client.delete(self._sid)
        except Exception as e:
            logger.error(f"Error clearing records: {e}")
