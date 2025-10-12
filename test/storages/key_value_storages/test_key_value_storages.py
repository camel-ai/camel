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

import tempfile
from pathlib import Path

import pytest

from camel.storages.key_value_storages import (
    BaseKeyValueStorage,
    InMemoryKeyValueStorage,
    JsonStorage,
)
from camel.types import RoleType


@pytest.fixture
def storage(request):
    if request.param == "in-memory":
        yield InMemoryKeyValueStorage()
    elif request.param == "json":
        _, path = tempfile.mkstemp()
        path = Path(path)
        yield JsonStorage(path)
        path.unlink()


@pytest.mark.parametrize("storage", ["in-memory", "json"], indirect=True)
def test_key_value_storage(storage: BaseKeyValueStorage):
    msg1 = {
        "key1": "value1",
        "role": RoleType.USER,
        "message": "Do a task",
        "additional_dict": {"1": 1, "2": 2},
    }
    msg2 = {
        "key1": "value2",
        "role": RoleType.ASSISTANT,
        "assistant_msg": "Ok",
    }
    storage.save([msg1, msg2])
    load_msg = storage.load()
    assert load_msg[0] == msg1
    assert load_msg[1] == msg2

    msg1_copy = msg1.copy()
    msg1.clear()
    assert load_msg[0] == msg1_copy

    storage.clear()
    load_msg = storage.load()
    assert load_msg == []


def test_in_memory_storage_deduplication():
    r"""Test InMemoryKeyValueStorage prevents duplicate records by UUID."""
    storage = InMemoryKeyValueStorage()

    # Create records with UUIDs
    record1 = {
        "uuid": "test-uuid-1",
        "message": "First message",
        "data": "some data",
    }
    record2 = {
        "uuid": "test-uuid-2",
        "message": "Second message",
        "data": "other data",
    }
    record1_duplicate = {
        "uuid": "test-uuid-1",  # Same UUID as record1
        "message": "Duplicate message",
        "data": "different data",
    }

    # Save initial records
    storage.save([record1, record2])
    loaded = storage.load()
    assert len(loaded) == 2

    # Try to save duplicate
    storage.save([record1_duplicate])
    loaded = storage.load()
    assert len(loaded) == 2  # Should still be 2, duplicate not added

    # Verify original record1 is intact (not overwritten)
    record1_loaded = next(r for r in loaded if r.get("uuid") == "test-uuid-1")
    assert record1_loaded["message"] == "First message"
    assert record1_loaded["data"] == "some data"

    # Save a new record with different UUID
    record3 = {
        "uuid": "test-uuid-3",
        "message": "Third message",
        "data": "new data",
    }
    storage.save([record3])
    loaded = storage.load()
    assert len(loaded) == 3

    # Test records without UUID (should be allowed)
    record_no_uuid = {
        "message": "No UUID message",
        "data": "no uuid data",
    }
    storage.save([record_no_uuid])
    loaded = storage.load()
    assert len(loaded) == 4

    # Clear and verify
    storage.clear()
    loaded = storage.load()
    assert len(loaded) == 0

    # After clear, should be able to add previously seen UUIDs again
    storage.save([record1])
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0]["uuid"] == "test-uuid-1"


def test_in_memory_storage_load_performance():
    r"""Test that load() returns a shallow copy for performance."""
    storage = InMemoryKeyValueStorage()

    # Create a large number of records
    records = [{"uuid": f"uuid-{i}", "data": f"data-{i}"} for i in range(100)]
    storage.save(records)

    # Load records
    loaded1 = storage.load()
    loaded2 = storage.load()

    # Verify content is correct
    assert len(loaded1) == 100
    assert len(loaded2) == 100

    # Modifying loaded list should not affect storage
    loaded1.append({"uuid": "new", "data": "new"})
    loaded2_after = storage.load()
    assert len(loaded2_after) == 100  # Still 100, not 101
