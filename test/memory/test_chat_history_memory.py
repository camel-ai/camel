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

import pytest

from camel.memory import ChatHistoryMemory, MemoryRecord
from camel.memory.dict_storage import InMemoryDictStorage, JsonStorage
from camel.messages import BaseMessage
from camel.typing import OpenAIBackendRole, RoleType


@pytest.fixture
def memory(request):
    if request.param == "in-memory":
        yield ChatHistoryMemory(storage=InMemoryDictStorage())
    elif request.param == "json":
        _, path = tempfile.mkstemp()
        path = Path(path)
        yield ChatHistoryMemory(storage=JsonStorage(path))
        path.unlink()


@pytest.mark.parametrize("memory", ["in-memory", "json"], indirect=True)
def test_chat_history_memory(memory: ChatHistoryMemory):
    system_msg = BaseMessage(
        "system",
        role_type=RoleType.DEFAULT,
        meta_dict=None,
        content="You are a helpful assistant",
    )
    user_msg = BaseMessage(
        "AI user",
        role_type=RoleType.USER,
        meta_dict=None,
        content="Do a task",
    )
    assistant_msg = BaseMessage(
        "AI assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="OK",
    )
    system_record = MemoryRecord(system_msg, OpenAIBackendRole.SYSTEM)
    user_record = MemoryRecord(user_msg, OpenAIBackendRole.USER)
    assistant_record = MemoryRecord(assistant_msg, OpenAIBackendRole.ASSISTANT)
    memory.write_records([system_record, user_record, assistant_record])
    load_msgs = memory.retrieve()
    assert asdict(load_msgs[0]) == asdict(system_record)
    assert asdict(load_msgs[1]) == asdict(user_record)
    assert asdict(load_msgs[2]) == asdict(assistant_record)
