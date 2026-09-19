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


def _make_record(content, ts):
    return ContextRecord(
        memory_record=MemoryRecord(
            message=BaseMessage(
                "test",
                RoleType.USER,
                meta_dict=None,
                content=content,
            ),
            role_at_backend=OpenAIBackendRole.USER,
        ),
        timestamp=ts,
        score=1.0,
    )


def test_cache_reused_for_identical_messages():
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 100_000
    )
    records = [_make_record("hi", 1.0), _make_record("hello", 2.0)]

    messages, real_tokens = context_creator.create_context(records)
    context_creator.set_cached_token_count(real_tokens, len(records))

    cached_messages, cached_tokens = context_creator.create_context(records)
    assert cached_messages == messages
    assert cached_tokens == real_tokens


def test_cache_invalidated_when_window_slides_with_constant_count():
    r"""A sliding memory window keeps the message count constant while
    replacing messages, and the cached total must not be returned for a
    different message set (issue #4328)."""
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 100_000
    )
    turn1 = [
        _make_record("hi", 1.0),
        _make_record("hello", 2.0),
        _make_record("ok", 3.0),
        _make_record("yes", 4.0),
    ]
    _, real_tokens1 = context_creator.create_context(turn1)
    context_creator.set_cached_token_count(real_tokens1, len(turn1))

    huge = "TOKEN " * 5000
    turn2 = [
        _make_record("hello", 2.0),
        _make_record("ok", 3.0),
        _make_record("yes", 4.0),
        _make_record(huge, 5.0),
    ]
    messages2, tokens2 = context_creator.create_context(turn2)

    real_tokens2 = context_creator.token_counter.count_tokens_from_messages(
        messages2
    )
    assert tokens2 == real_tokens2
    assert tokens2 != real_tokens1


def test_cache_exact_when_context_grows_by_calibrated_response():
    r"""Mirrors the ``ChatAgent`` protocol: the cached count describes the
    calibrated message set plus one assistant response, so the next context
    that strictly appends that response reuses the exact cached value."""
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 100_000
    )
    records1 = [
        _make_record("hi", 1.0),
        _make_record("hello", 2.0),
        _make_record("ok", 3.0),
    ]
    messages1, real_tokens1 = context_creator.create_context(records1)
    context_creator.set_cached_token_count(real_tokens1, len(messages1) + 1)

    records2 = [*records1, _make_record("appended reply", 4.0)]
    _, tokens2 = context_creator.create_context(records2)

    assert tokens2 == real_tokens1


def test_cache_estimates_only_strictly_appended_messages():
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(ModelType.GPT_4O_MINI), 100_000
    )
    records1 = [
        _make_record("hi", 1.0),
        _make_record("hello", 2.0),
        _make_record("ok", 3.0),
    ]
    messages1, real_tokens1 = context_creator.create_context(records1)
    context_creator.set_cached_token_count(real_tokens1, len(messages1))

    records2 = [*records1, _make_record("newly appended", 4.0)]
    messages2, tokens2 = context_creator.create_context(records2)

    expected = real_tokens1 + context_creator._estimate_message_tokens(
        messages2[-1]
    )
    assert tokens2 == expected
