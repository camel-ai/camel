# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from datetime import datetime

from camel.memories import (
    ContextRecord,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage
from camel.types import ModelType, OpenAIBackendRole, RoleType
from camel.utils import OpenAITokenCounter


def test_score_based_context_creator():
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4), 15
    )
    context_records = [
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="Nice to meet you.",  # 12
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            timestamp=datetime.now().timestamp(),
            score=0.3,
        ),
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="Hello world!",  # 10
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            timestamp=datetime.now().timestamp() + 1,
            score=0.9,
        ),
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="How are you?",  # 11
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            timestamp=datetime.now().timestamp() + 2,
            score=0.7,
        ),
    ]

    expected_output = [
        record.memory_record.to_openai_message()
        for record in sorted(context_records, key=lambda r: r.timestamp)
    ]
    output, _ = context_creator.create_context(records=context_records)
    assert expected_output == output


def test_score_based_context_creator_with_system_message():
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4), 40
    )
    context_records = [
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="You are a helpful assistant.",  # 12
                ),
                role_at_backend=OpenAIBackendRole.SYSTEM,
            ),
            timestamp=datetime.now().timestamp(),
            score=1,
        ),
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="Nice to meet you.",  # 12
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            timestamp=datetime.now().timestamp(),
            score=0.3,
        ),
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="Hello world!",  # 10
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            timestamp=datetime.now().timestamp() + 1,
            score=0.7,
        ),
        ContextRecord(
            memory_record=MemoryRecord(
                message=BaseMessage(
                    "test",
                    RoleType.ASSISTANT,
                    meta_dict=None,
                    content="How are you?",  # 11
                ),
                role_at_backend=OpenAIBackendRole.ASSISTANT,
            ),
            timestamp=datetime.now().timestamp() + 2,
            score=0.9,
        ),
    ]
    sorted_records = sorted(
        (record for record in context_records[1:]),
        key=lambda r: r.timestamp,
    )
    expected_output = [
        context_records[0].memory_record.to_openai_message(),
        *(
            record.memory_record.to_openai_message()
            for record in sorted_records
        ),
    ]
    output, _ = context_creator.create_context(records=context_records)
    assert expected_output == output


def test_cached_token_count_is_dropped_when_messages_are_removed():
    r"""A context that shrinks invalidates the cached count, so a later context
    with the same message count as the cached one must be recounted instead of
    being answered with the stale value.
    """

    class FixedTokenCounter:
        def __init__(self):
            self.calls = 0

        def count_tokens_from_messages(self, messages, tools=None):
            self.calls += 1
            return 42

    counter = FixedTokenCounter()
    context_creator = ScoreBasedContextCreator(counter, 1000)
    context_creator.set_cached_token_count(token_count=1000, message_count=5)

    def records(count):
        return [
            ContextRecord(
                memory_record=MemoryRecord(
                    message=BaseMessage.make_user_message(
                        role_name="user", content=f"message {i}"
                    ),
                    role_at_backend=OpenAIBackendRole.USER,
                ),
                timestamp=float(i),
                score=1.0,
            )
            for i in range(count)
        ]

    _, cached_tokens = context_creator.create_context(records(5))
    assert cached_tokens == 1000

    _, after_removal = context_creator.create_context(records(4))
    assert after_removal == 42

    _, after_regrowth = context_creator.create_context(records(5))
    assert after_regrowth == 42, "stale cached count was reused"
    assert counter.calls == 2
