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
from datetime import datetime
from pathlib import Path

import pytest

from camel.memories import ChatHistoryMemory, MemoryRecord
from camel.memories.context_creators import ScoreBasedContextCreator
from camel.messages import BaseMessage
from camel.storages.key_value_storages import (
    InMemoryKeyValueStorage,
    JsonStorage,
)
from camel.types import ModelType, OpenAIBackendRole, RoleType
from camel.utils.token_counting import OpenAITokenCounter


@pytest.fixture
def memory(request):
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4),
        ModelType.GPT_4.token_limit,
    )
    if request.param == "in-memory":
        yield ChatHistoryMemory(
            context_creator=context_creator, storage=InMemoryKeyValueStorage()
        )
    elif request.param == "json":
        _, path = tempfile.mkstemp()
        path = Path(path)
        yield ChatHistoryMemory(
            context_creator=context_creator, storage=JsonStorage(path)
        )
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
    system_record = MemoryRecord(
        message=system_msg,
        role_at_backend=OpenAIBackendRole.SYSTEM,
        timestamp=datetime.now().timestamp(),
        agent_id="system_agent_1",
    )
    user_record = MemoryRecord(
        message=user_msg,
        role_at_backend=OpenAIBackendRole.USER,
        timestamp=datetime.now().timestamp(),
        agent_id="user_agent_1",
    )
    assistant_record = MemoryRecord(
        message=assistant_msg,
        role_at_backend=OpenAIBackendRole.ASSISTANT,
        timestamp=datetime.now().timestamp(),
        agent_id="assistant_agent_1",
    )
    memory.write_records([system_record, user_record, assistant_record])
    output_messages, _ = memory.get_context()
    assert output_messages[0] == system_msg.to_openai_system_message()
    assert output_messages[1] == user_msg.to_openai_user_message()
    assert output_messages[2] == assistant_msg.to_openai_assistant_message()


@pytest.mark.parametrize("memory", ["in-memory", "json"], indirect=True)
def test_chat_history_memory_pop_records(memory: ChatHistoryMemory):
    system_msg = BaseMessage(
        "system",
        role_type=RoleType.DEFAULT,
        meta_dict=None,
        content="System instructions",
    )
    user_msgs = [
        BaseMessage(
            "AI user",
            role_type=RoleType.USER,
            meta_dict=None,
            content=f"Message {idx}",
        )
        for idx in range(3)
    ]

    records = [
        MemoryRecord(
            message=system_msg,
            role_at_backend=OpenAIBackendRole.SYSTEM,
            timestamp=datetime.now().timestamp(),
            agent_id="system",
        ),
        *[
            MemoryRecord(
                message=msg,
                role_at_backend=OpenAIBackendRole.USER,
                timestamp=datetime.now().timestamp(),
                agent_id="user",
            )
            for msg in user_msgs
        ],
    ]

    memory.write_records(records)

    popped = memory.pop_records(2)
    assert [record.message.content for record in popped] == [
        "Message 1",
        "Message 2",
    ]

    remaining_messages, _ = memory.get_context()
    assert [msg['content'] for msg in remaining_messages] == [
        "System instructions",
        "Message 0",
    ]

    # Attempting to pop more than available should leave system message intact.
    popped = memory.pop_records(5)
    assert [record.message.content for record in popped] == ["Message 0"]

    remaining_messages, _ = memory.get_context()
    assert [msg['content'] for msg in remaining_messages] == [
        "System instructions",
    ]

    # Zero pop should be a no-op.
    assert memory.pop_records(0) == []

    with pytest.raises(ValueError):
        memory.pop_records(-1)
