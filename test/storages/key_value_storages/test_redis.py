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
import asyncio

from camel.storages.key_value_storages import RedisStorage


@pytest.fixture
def sid():
    return "test_sid"


@pytest.fixture
async def redis_storage(sid):
    async with RedisStorage(sid) as storage:
        await storage.clear()
        yield storage
        await storage.clear()


@pytest.mark.asyncio
async def test_save_load(redis_storage):
    records = [{"id": 1, "name": "Record1"}, {"id": 2, "name": "Record2"}]
    await redis_storage.save(records)
    loaded_records = await redis_storage.load()
    assert loaded_records == records


@pytest.mark.asyncio
async def test_save_with_expiration(redis_storage):
    records = [{"id": 1, "name": "Record1"}]
    await redis_storage.save(records, expire=1)
    await asyncio.sleep(2)
    loaded_records = await redis_storage.load()
    assert loaded_records == []


@pytest.mark.asyncio
async def test_load_empty(redis_storage):
    loaded_records = await redis_storage.load()
    assert loaded_records == []


@pytest.mark.asyncio
async def test_clear(redis_storage):
    records = [{"id": 1, "name": "Record1"}]
    await redis_storage.save(records)
    await redis_storage.clear()
    loaded_records = await redis_storage.load()
    assert loaded_records == []
