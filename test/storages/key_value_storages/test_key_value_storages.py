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


def test_in_memory_storage_deep_copy_protection():
    r"""Test that load() and save() use deep copy to prevent data mutations."""
    storage = InMemoryKeyValueStorage()

    # Test 1: Deep copy on save() prevents input mutation affecting storage
    input_record = {"uuid": "test-1", "data": {"nested": "value"}}
    storage.save([input_record])

    # Mutate the input record
    input_record["data"]["nested"] = "MUTATED_INPUT"

    # Storage should be unaffected
    loaded = storage.load()
    assert loaded[0]["data"]["nested"] == "value"

    # Test 2: Deep copy on load() prevents output mutation affecting storage
    loaded1 = storage.load()
    loaded1[0]["data"]["nested"] = "MUTATED_OUTPUT"

    # Storage should be unaffected
    loaded2 = storage.load()
    assert loaded2[0]["data"]["nested"] == "value"

    # Test 3: Modifying loaded list should not affect storage
    loaded3 = storage.load()
    loaded3.append({"uuid": "new", "data": "new"})
    loaded4 = storage.load()
    assert len(loaded4) == 1  # Still 1, not 2
