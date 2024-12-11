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
