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

from camel.memories import (
    ContextRecord,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole, PredefinedModelType, RoleType
from camel.utils import OpenAITokenCounter


def test_score_based_context_creator():
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(PredefinedModelType.GPT_4), 21
    )
    context_records = [
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
            score=0.9,
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
            score=0.3,
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
            score=0.7,
        ),
    ]

    expected_output = [
        r.memory_record.to_openai_message()
        for r in [context_records[0], context_records[2]]
    ]
    output, _ = context_creator.create_context(records=context_records)
    assert expected_output == output
