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

import asyncio

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
def redis_storage(sid):
    return RedisStorage(sid=sid, loop=asyncio.get_event_loop())


def test_save(redis_storage):
    records_to_save = [{"key1": "value1"}, {"key2": "value2"}]
    redis_storage.save(records_to_save)

    loaded_records = redis_storage.load()
    assert loaded_records == records_to_save


def test_load(redis_storage):
    records_to_save = [{"key3": "value3"}, {"key4": "value4"}]
    redis_storage.save(records_to_save)

    loaded_records = redis_storage.load()
    assert loaded_records == records_to_save


def test_clear(redis_storage):
    records_to_save = [{"key5": "value5"}, {"key6": "value6"}]
    redis_storage.save(records_to_save)

    redis_storage.clear()

    loaded_records_after_clear = redis_storage.load()
    assert loaded_records_after_clear == []
