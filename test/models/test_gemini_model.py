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

import pytest

from camel.configs import GeminiConfig
from camel.models import GeminiModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GEMINI_2_5_PRO,
        ModelType.GEMINI_2_0_FLASH,
        ModelType.GEMINI_2_0_FLASH_THINKING,
        ModelType.GEMINI_2_0_FLASH_LITE_PREVIEW,
        ModelType.GEMINI_2_0_PRO_EXP,
    ],
)
def test_gemini_model(model_type: ModelType):
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_gemini_process_messages_merges_parallel_tool_calls():
    r"""Test that _process_messages merges consecutive assistant messages with
    single tool calls into a single assistant message with multiple tool calls.

    This is required for Gemini's OpenAI-compatible API for parallel function
    calling.
    """
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(ModelType.GEMINI_3_PRO, model_config_dict)

    # Simulate messages where ChatAgent recorded parallel tool calls as
    # separate assistant messages (the default behavior)
    messages = [
        {"role": "user", "content": "Calculate 2+2 and 3*3"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "math_add",
                        "arguments": '{"a": 2, "b": 2}',
                    },
                    "extra_content": {
                        "google": {"thought_signature": "sig_A"}
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "content": "4",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_002",
                    "type": "function",
                    "function": {
                        "name": "math_multiply",
                        "arguments": '{"a": 3, "b": 3}',
                    },
                    "extra_content": {
                        "google": {"thought_signature": "sig_B"}
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_002",
            "content": "9",
        },
    ]

    processed = model._process_messages(messages)

    # Should have: user, assistant (merged), tool, tool
    assert len(processed) == 4

    # First message is user
    assert processed[0]['role'] == 'user'

    # Second message should be assistant with merged tool_calls
    assistant_msg = processed[1]
    assert assistant_msg['role'] == 'assistant'
    assert len(assistant_msg['tool_calls']) == 2

    # First tool call should have extra_content
    assert 'extra_content' in assistant_msg['tool_calls'][0]
    assert (
        assistant_msg['tool_calls'][0]['extra_content']['google'][
            'thought_signature'
        ]
        == 'sig_A'
    )

    # Second tool call should NOT have extra_content (Gemini requirement)
    assert 'extra_content' not in assistant_msg['tool_calls'][1]

    # Tool results should follow
    assert processed[2]['role'] == 'tool'
    assert processed[2]['tool_call_id'] == 'call_001'
    assert processed[3]['role'] == 'tool'
    assert processed[3]['tool_call_id'] == 'call_002'


@pytest.mark.model_backend
def test_gemini_process_messages_single_tool_call_unchanged():
    r"""Test that _process_messages preserves single tool calls unchanged."""
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(ModelType.GEMINI_3_PRO, model_config_dict)

    messages = [
        {"role": "user", "content": "Calculate 2+2"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "math_add",
                        "arguments": '{"a": 2, "b": 2}',
                    },
                    "extra_content": {
                        "google": {"thought_signature": "sig_A"}
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "content": "4",
        },
    ]

    processed = model._process_messages(messages)

    # Should remain unchanged: user, assistant, tool
    assert len(processed) == 3

    assistant_msg = processed[1]
    assert assistant_msg['role'] == 'assistant'
    assert len(assistant_msg['tool_calls']) == 1
    assert 'extra_content' in assistant_msg['tool_calls'][0]
