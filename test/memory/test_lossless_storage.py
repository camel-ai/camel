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

import tempfile
from pathlib import Path

from camel.memory.lossless_storage import InMemoryStorage, JsonStorage
from camel.typing import RoleType


def test_in_memory_storage():
    in_memory = InMemoryStorage()
    msg1 = {
        "key1": "value1",
        "role": RoleType.USER,
        "message": "Do a task",
        "additional_dict": {
            "1": 1,
            "2": 2
        },
    }
    msg2 = {
        "key1": "value2",
        "role": RoleType.ASSISTANT,
        "assistant_msg": "Ok",
    }
    in_memory.save([msg1, msg2])
    load_msg = in_memory.load()
    assert load_msg[0] == msg1
    assert load_msg[1] == msg2

    msg1_copy = msg1.copy()
    msg1.clear()
    assert load_msg[0] == msg1_copy

    in_memory.clear()
    load_msg = in_memory.load()
    assert load_msg == []


def test_json_storage():
    _, path = tempfile.mkstemp()
    path = Path(path)
    json_storage = JsonStorage(path)
    msg1 = {
        "key1": "value1",
        "role": RoleType.USER,
        "message": "Do a task",
        "additional_dict": {
            "1": 1,
            "2": 2
        },
    }
    msg2 = {
        "key1": "value2",
        "role": RoleType.ASSISTANT,
        "assistant_msg": "Ok",
    }
    json_storage.save([msg1, msg2])
    assert path.read_text() != ""

    load_msg = json_storage.load()
    assert load_msg[0] == msg1
    assert load_msg[1] == msg2

    json_storage.clear()
    load_msg = json_storage.load()
    assert load_msg == []

    path.unlink()
