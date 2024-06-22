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

import pytest
from camel.storages.cache_storages import RedisStorage


@pytest.fixture
async def redis_storage():
    async with RedisStorage() as storage:
        yield storage
        await storage.clear_cache()


@pytest.mark.asyncio
async def test_set_cache(redis_storage):
    result = await redis_storage.set_cache('test_key', {'name': 'Alice', 'age': 30}, expire=3600)
    assert result is True


@pytest.mark.asyncio
async def test_get_cache(redis_storage):
    await redis_storage.set_cache('test_key', {'name': 'Alice', 'age': 30}, expire=3600)
    value = await redis_storage.get_cache('test_key')
    assert value == {'name': 'Alice', 'age': 30}


@pytest.mark.asyncio
async def test_delete_cache(redis_storage):
    await redis_storage.set_cache('test_key', {'name': 'Alice', 'age': 30}, expire=3600)
    result = await redis_storage.delete_cache('test_key')
    assert result is True
    value = await redis_storage.get_cache('test_key')
    assert value is None


@pytest.mark.asyncio
async def test_delete_non_existing_key(redis_storage):
    result = await redis_storage.delete_cache('non_existing_key')
    assert result is True
    value = await redis_storage.get_cache('non_existing_key')
    assert value is None


@pytest.mark.asyncio
async def test_clear_cache(redis_storage):
    await redis_storage.set_cache('test_key1', {'name': 'Alice', 'age': 30}, expire=3600)
    await redis_storage.set_cache('test_key2', {'name': 'Bob', 'age': 25}, expire=3600)
    await redis_storage.clear_cache()
    value1 = await redis_storage.get_cache('test_key1')
    value2 = await redis_storage.get_cache('test_key2')
    assert value1 is None
    assert value2 is None
