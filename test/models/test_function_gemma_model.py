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
from unittest.mock import MagicMock

import pytest

from camel.models import FunctionGemmaModel


def _model() -> FunctionGemmaModel:
    return FunctionGemmaModel("functiongemma")


@pytest.mark.parametrize(
    "done_reason,expected",
    [
        ("length", "length"),
        ("stop", "stop"),
        (None, "stop"),
        ("unknown_future_value", "stop"),
    ],
)
def test_map_done_reason(done_reason, expected):
    assert FunctionGemmaModel._map_done_reason(done_reason) == expected


def test_to_chat_completion_surfaces_real_usage_and_truncation():
    r"""Ollama's real prompt_eval_count/eval_count/done_reason must reach
    the returned ChatCompletion, not the hardcoded zero usage / 'stop'
    finish_reason the backend used to return unconditionally."""
    model = _model()

    result = model._to_chat_completion(
        "The answer is 4.",
        "functiongemma",
        tools=None,
        ollama_result={
            "response": "The answer is 4.",
            "done": True,
            "done_reason": "length",
            "prompt_eval_count": 37,
            "eval_count": 128,
        },
    )

    assert result.usage.prompt_tokens == 37
    assert result.usage.completion_tokens == 128
    assert result.usage.total_tokens == 165
    assert result.choices[0].finish_reason == "length"


def test_to_chat_completion_tool_calls_override_done_reason():
    r"""A parsed tool call must still win over done_reason, matching the
    prior unconditional tool_calls behavior."""
    model = _model()
    tools = [
        {
            "type": "function",
            "function": {"name": "get_weather", "parameters": {}},
        }
    ]

    result = model._to_chat_completion(
        "<start_function_call>call:get_weather{}<end_function_call>",
        "functiongemma",
        tools=tools,
        ollama_result={
            "done_reason": "length",
            "prompt_eval_count": 10,
            "eval_count": 5,
        },
    )

    assert result.choices[0].finish_reason == "tool_calls"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5


def test_to_chat_completion_no_ollama_result_defaults_preserved():
    r"""Callers that pass no ollama_result keep the old zero-usage/'stop'
    defaults (backward compatible with any external caller of this
    method)."""
    model = _model()

    result = model._to_chat_completion(
        "hello", "functiongemma", tools=None, ollama_result=None
    )

    assert result.usage.prompt_tokens == 0
    assert result.usage.completion_tokens == 0
    assert result.usage.total_tokens == 0
    assert result.choices[0].finish_reason == "stop"


def test_run_plumbs_ollama_usage_and_truncation_end_to_end():
    r"""End-to-end: a mocked /api/generate response with real usage and a
    truncation done_reason must not be discarded by _run."""
    model = _model()
    model._client.post = MagicMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={
                    "response": "The answer is 4.",
                    "done": True,
                    "done_reason": "length",
                    "prompt_eval_count": 37,
                    "eval_count": 128,
                }
            ),
        )
    )

    response = model._run(
        messages=[{"role": "user", "content": "what is 2+2?"}],
        tools=None,
    )

    assert response.usage.prompt_tokens == 37
    assert response.usage.completion_tokens == 128
    assert response.choices[0].finish_reason == "length"
