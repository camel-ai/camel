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
from dataclasses import asdict
from pathlib import Path

from camel.memory import ChatHistoryMemory
from camel.memory.lossless_storage import JsonStorage
from camel.messages import BaseMessage
from camel.typing import RoleType


def test_chat_history_memory():
    memory = ChatHistoryMemory()
    user_msg = BaseMessage("AI user", role_type=RoleType.USER,
                           meta_dict={"key": "value"}, content="Do a task")
    assistant_msg = BaseMessage("AI assistant", role_type=RoleType.ASSISTANT,
                                meta_dict={"key2": "value2"}, content="OK")
    memory.write([user_msg, assistant_msg])
    load_msgs = memory.read()
    assert asdict(load_msgs[0]) == asdict(user_msg)
    assert asdict(load_msgs[1]) == asdict(assistant_msg)


def test_chat_history_memory_json_storage():
    _, path = tempfile.mkstemp()
    path = Path(path)
    storage = JsonStorage(path)
    memory = ChatHistoryMemory(storage=storage)
    user_msg = BaseMessage("AI user", role_type=RoleType.USER,
                           meta_dict={"key": "value"}, content="Do a task")
    assistant_msg = BaseMessage("AI assistant", role_type=RoleType.ASSISTANT,
                                meta_dict={"key2": "value2"}, content="OK")
    memory.write([user_msg, assistant_msg])
    load_msgs = memory.read()
    assert asdict(load_msgs[0]) == asdict(user_msg)
    assert asdict(load_msgs[1]) == asdict(assistant_msg)

    path = Path(path)
