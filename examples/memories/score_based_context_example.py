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

from datetime import datetime

from camel.memories import (
    ContextRecord,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage
from camel.types import ModelType, OpenAIBackendRole, RoleType
from camel.utils import OpenAITokenCounter

# set token limit to 300
context_creator = ScoreBasedContextCreator(
    OpenAITokenCounter(ModelType.GPT_4), 300
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

output, _ = context_creator.create_context(records=context_records)

print(output)
"""
===============================================================================
[{'role': 'assistant', 'content': 'Nice to meet you.'}, {'role': 'assistant', 
'content': 'Hello world!'}, {'role': 'assistant', 'content': 'How are you?'}]
===============================================================================
"""


# set token limit to 21
context_creator = ScoreBasedContextCreator(
    OpenAITokenCounter(ModelType.GPT_4), 21
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

output, _ = context_creator.create_context(records=context_records)

print(output)
"""
===============================================================================
Context truncation required (33 > 21), pruning low-score messages.
[{'role': 'assistant', 'content': 'Hello world!'}, {'role': 'assistant', 
'content': 'How are you?'}]
===============================================================================
"""


# set token limit to 40
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

output, _ = context_creator.create_context(records=context_records)

print(output)
"""
===============================================================================
Context truncation required (46 > 40), pruning low-score messages.
[{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 
'assistant', 'content': 'Hello world!'}, {'role': 'assistant', 'content': 'How 
are you?'}]
===============================================================================
"""


# set token limit to 14
context_creator = ScoreBasedContextCreator(
    OpenAITokenCounter(ModelType.GPT_4), 14
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

output, _ = context_creator.create_context(records=context_records)

print(output)
"""
===============================================================================
RuntimeError: ('System message and current message exceeds token limit ', 46)
===============================================================================
"""
