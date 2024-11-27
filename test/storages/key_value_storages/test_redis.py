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

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from camel.storages.key_value_storages import RedisStorage


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sid():
    return "test_sid"


@pytest.fixture
def mock_redis_client():
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def redis_storage(sid, mock_redis_client):
    with patch(
        'camel.storages.key_value_storages.RedisStorage._create_client'
    ) as create_client_mock:
        create_client_mock.return_value = None
        storage = RedisStorage(sid=sid, loop=asyncio.get_event_loop())
        storage._client = mock_redis_client
        yield storage


def test_save(sid, redis_storage, mock_redis_client):
    records_to_save = [{"key1": "value1"}, {"key2": "value2"}]
    redis_storage.save(records_to_save)

    mock_redis_client.set.assert_called_once_with(
        sid, json.dumps(records_to_save)
    )


def test_load(redis_storage, mock_redis_client):
    records_to_save = [{"key3": "value3"}, {"key4": "value4"}]
    mock_redis_client.get.return_value = json.dumps(records_to_save)

    loaded_records = redis_storage.load()
    assert loaded_records == records_to_save


def test_clear(sid, redis_storage, mock_redis_client):
    redis_storage.clear()

    mock_redis_client.delete.assert_called_once_with(sid)
