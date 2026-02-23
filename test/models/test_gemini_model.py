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
def test_gemini_process_messages_merges_parallel_split():
    r"""Test that _process_messages re-groups split parallel tool calls.

    Gemini 3 returns parallel calls as FC1+sig, FC2 (no sig) in one
    response.  ChatAgent may split them into separate assistant→tool pairs.
    _process_messages must merge them back:

        A(FC1+sig)→T1→A(FC2, no sig)→T2  →  A(FC1+sig, FC2)→T1→T2

    The interleaved form triggers a 400 from the Gemini API.
    """
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(ModelType.GEMINI_3_PRO, model_config_dict)

    messages = [
        {"role": "user", "content": "Weather in Paris and London"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "Paris"}',
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
            "content": '{"temp": "15C"}',
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_002",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "London"}',
                    },
                    # No extra_content / thought_signature → parallel companion
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_002",
            "content": '{"temp": "12C"}',
        },
    ]

    processed = model._process_messages(messages)

    # Should be: user, assistant(2 tool_calls), tool, tool
    assert len(processed) == 4
    assert processed[0]["role"] == "user"

    assistant_msg = processed[1]
    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["tool_calls"]) == 2
    # First call keeps its signature
    assert (
        assistant_msg["tool_calls"][0]["extra_content"]["google"][
            "thought_signature"
        ]
        == "sig_A"
    )
    # Second call has no signature (as the model returned it)
    assert "extra_content" not in assistant_msg["tool_calls"][1]

    assert processed[2]["role"] == "tool"
    assert processed[2]["tool_call_id"] == "call_001"
    assert processed[3]["role"] == "tool"
    assert processed[3]["tool_call_id"] == "call_002"


@pytest.mark.model_backend
def test_gemini_process_messages_preserves_sequential_calls():
    r"""Test that _process_messages does NOT merge sequential calls.

    Sequential steps each carry their own thought_signature.  Merging them
    would break the per-step signature positioning required by Gemini 3.
    """
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(ModelType.GEMINI_3_PRO, model_config_dict)

    messages = [
        {"role": "user", "content": "First add, then multiply"},
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
                        "google": {"thought_signature": "sig_step1"}
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
                        "arguments": '{"a": 4, "b": 3}',
                    },
                    # Has its own signature → new sequential step
                    "extra_content": {
                        "google": {"thought_signature": "sig_step2"}
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_002",
            "content": "12",
        },
    ]

    processed = model._process_messages(messages)

    # All 5 messages preserved (no merging)
    assert len(processed) == 5
    assert processed[0]["role"] == "user"
    assert processed[1]["role"] == "assistant"
    assert len(processed[1]["tool_calls"]) == 1
    assert processed[2]["role"] == "tool"
    assert processed[3]["role"] == "assistant"
    assert len(processed[3]["tool_calls"]) == 1
    assert processed[4]["role"] == "tool"


@pytest.mark.model_backend
def test_gemini_process_messages_no_signature_unchanged():
    r"""Test that messages without thought_signature are left untouched.

    For non-thinking models the parallel/sequential distinction is
    ambiguous, so we leave the interleaved format as-is (accepted by
    non-thinking models).
    """
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(ModelType.GEMINI_3_PRO, model_config_dict)

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
                },
            ],
        },
        {"role": "tool", "tool_call_id": "call_001", "content": "4"},
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
                },
            ],
        },
        {"role": "tool", "tool_call_id": "call_002", "content": "9"},
    ]

    processed = model._process_messages(messages)

    # No signatures → no merging, all 5 messages preserved
    assert len(processed) == 5


@pytest.mark.model_backend
def test_gemini_convert_merges_consecutive_same_role_contents():
    r"""Test that _convert_openai_messages_to_genai merges consecutive
    Contents with the same role (e.g. multiple tool results become a single
    user Content with multiple function_response Parts).
    """
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(ModelType.GEMINI_3_PRO, model_config_dict)

    # An assistant message with two parallel tool calls followed by
    # two tool results.  The two tool messages would each produce a
    # user Content; they must be merged.
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
                {
                    "id": "call_002",
                    "type": "function",
                    "function": {
                        "name": "math_multiply",
                        "arguments": '{"a": 3, "b": 3}',
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
            "role": "tool",
            "tool_call_id": "call_002",
            "content": "9",
        },
    ]

    system_instruction, contents = model._convert_openai_messages_to_genai(
        messages
    )

    # user, model, user (two tool results merged into one)
    assert len(contents) == 3
    assert contents[0].role == "user"
    assert contents[1].role == "model"
    # The merged user Content should have 2 function_response parts
    assert contents[2].role == "user"
    assert len(contents[2].parts) == 2


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
    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["tool_calls"]) == 1
    assert "extra_content" in assistant_msg["tool_calls"][0]
