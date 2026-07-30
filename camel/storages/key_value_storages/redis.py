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

import asyncio
import json
import logging
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.storages.key_value_storages import BaseKeyValueStorage
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisStorage(BaseKeyValueStorage):
    r"""A concrete implementation of the :obj:`BaseCacheStorage` using Redis as
    the backend. This is suitable for distributed cache systems that require
    persistence and high availability.
    """

    @dependencies_required('redis')
    def __init__(
        self,
        sid: str,
        url: str = "redis://localhost:6379",
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs,
    ) -> None:
        r"""Initializes the RedisStorage instance with the provided URL and
        options.

        Args:
            sid (str): The ID for the storage instance to identify the
                       record space.
            url (str): The URL for connecting to the Redis server.
            **kwargs: Additional keyword arguments for Redis client
                      configuration.

        Raises:
            ImportError: If the `redis` module is not installed.
        """
        import redis.asyncio as aredis

        self._client: Optional[aredis.Redis] = None
        self._url = url
        self._sid = sid
        # A loop is no longer captured eagerly. ``asyncio.get_event_loop()``
        # raises in a thread that has none, and a loop captured at
        # construction time is the wrong one to wait on if the caller later
        # runs a different loop on the same thread. When no loop is supplied,
        # one is created on a background thread on first use instead.
        self._loop = loop
        self._owned_loop: Optional[asyncio.AbstractEventLoop] = None
        self._owned_thread: Optional[threading.Thread] = None
        self._owned_loop_lock = threading.Lock()

        self._create_client(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self._run_async(self.close())
        finally:
            # The background loop runs on a daemon thread, so leaving it alive
            # would not block interpreter exit, but a caller who scopes the
            # storage with ``with`` should not be left with a thread per
            # instance either.
            self._close_background_loop()

    async def close(self) -> None:
        r"""Closes the Redis client asynchronously."""
        if self._client:
            await self._client.close()

    def _create_client(self, **kwargs) -> None:
        r"""Creates the Redis client with the provided URL and options.

        Args:
            **kwargs: Additional keyword arguments for Redis client
                      configuration.
        """
        import redis.asyncio as aredis

        self._client = aredis.from_url(self._url, **kwargs)

    @property
    def client(self) -> Optional["Redis"]:
        r"""Returns the Redis client instance.

        Returns:
            redis.asyncio.Redis: The Redis client instance.
        """
        return self._client

    def save(
        self, records: List[Dict[str, Any]], expire: Optional[int] = None
    ) -> None:
        r"""Saves a batch of records to the key-value storage system."""
        try:
            self._run_async(self._async_save(records, expire))
        except Exception as e:
            logger.error(f"Error in save: {e}")

    def load(self) -> List[Dict[str, Any]]:
        r"""Loads all stored records from the key-value storage system.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                represents a stored record.
        """
        try:
            return self._run_async(self._async_load())
        except Exception as e:
            logger.error(f"Error in load: {e}")
            return []

    def clear(self) -> None:
        r"""Removes all records from the key-value storage system."""
        try:
            self._run_async(self._async_clear())
        except Exception as e:
            logger.error(f"Error in clear: {e}")

    async def _async_save(
        self, records: List[Dict[str, Any]], expire: Optional[int] = None
    ) -> None:
        if self._client is None:
            raise ValueError("Redis client is not initialized")
        try:
            value = json.dumps(records, ensure_ascii=False)
            if expire:
                await self._client.setex(self._sid, expire, value)
            else:
                await self._client.set(self._sid, value)
        except Exception as e:
            logger.error(f"Error saving records: {e}")

    async def _async_load(self) -> List[Dict[str, Any]]:
        if self._client is None:
            raise ValueError("Redis client is not initialized")
        try:
            value = await self._client.get(self._sid)
            if value:
                return json.loads(value)
            return []
        except Exception as e:
            logger.error(f"Error loading records: {e}")
            return []

    async def _async_clear(self) -> None:
        if self._client is None:
            raise ValueError("Redis client is not initialized")
        try:
            await self._client.delete(self._sid)
        except Exception as e:
            logger.error(f"Error clearing records: {e}")

    def _background_loop(self) -> asyncio.AbstractEventLoop:
        r"""Returns this instance's loop, starting it on first use.

        The loop lives on a daemon thread for the lifetime of the storage, so
        every coroutine runs on the same loop. ``redis.asyncio`` binds its
        connection pool to the loop that first uses it, so a fresh loop per
        call would discard the pool and can leave the previous loop's
        connections unusable.
        """
        with self._owned_loop_lock:
            if self._owned_loop is None or self._owned_loop.is_closed():
                loop = asyncio.new_event_loop()
                started = threading.Event()

                def run() -> None:
                    asyncio.set_event_loop(loop)
                    loop.call_soon(started.set)
                    loop.run_forever()

                thread = threading.Thread(
                    target=run,
                    name=f"camel-redis-{self._sid}",
                    daemon=True,
                )
                thread.start()
                # The loop must be confirmed running before it is returned:
                # a caller that sees ``is_running() is False`` would try to
                # drive it with ``run_until_complete`` from its own thread.
                started.wait(timeout=10)
                self._owned_loop = loop
                self._owned_thread = thread
            return self._owned_loop

    def _run_async(self, coro):
        r"""Runs a coroutine from a synchronous caller.

        A caller-supplied loop is used when it can be, so an application that
        passes its own loop keeps its Redis traffic there. Two situations rule
        it out, and both used to fail:

        - it is the loop running in *this* thread. ``.result()`` would occupy
          the very thread that loop needs in order to advance the coroutine,
          so the call would hang forever.
        - it is idle while this thread runs some other loop.
          ``run_until_complete`` refuses to drive a second loop on a thread
          that is already running one.

        In either case the coroutine goes to the background loop, which runs
        on a thread of its own and so is never the one being blocked.
        """
        try:
            running_loop: Optional[asyncio.AbstractEventLoop] = (
                asyncio.get_running_loop()
            )
        except RuntimeError:
            running_loop = None

        supplied = self._loop
        if (
            supplied is None
            or supplied.is_closed()
            or supplied is running_loop
            or (running_loop is not None and not supplied.is_running())
        ):
            loop = self._background_loop()
        else:
            loop = supplied

        if loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        return loop.run_until_complete(coro)

    def _close_background_loop(self) -> None:
        r"""Stops the background event loop, if one was started."""
        with self._owned_loop_lock:
            loop, thread = self._owned_loop, self._owned_thread
            self._owned_loop, self._owned_thread = None, None

        if loop is None:
            return
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=5)
        loop.close()
