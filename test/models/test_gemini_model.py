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
from pydantic import BaseModel

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


@pytest.mark.model_backend
def test_gemini_config_accepts_cache_parameters():
    r"""Test that GeminiConfig accepts cache_control and cached_content
    parameters.
    """
    config = GeminiConfig(
        temperature=0.5,
        cache_control="300s",
        cached_content="cachedContents/abc123",
    )
    config_dict = config.as_dict()

    assert config_dict["cache_control"] == "300s"
    assert config_dict["cached_content"] == "cachedContents/abc123"
    assert config_dict["temperature"] == 0.5


@pytest.mark.model_backend
def test_gemini_model_extracts_cache_params():
    r"""Test that GeminiModel extracts cache params from config and stores
    them.
    """
    model_config_dict = GeminiConfig(
        temperature=0.5,
        cache_control="300s",
        cached_content="cachedContents/abc123",
    ).as_dict()

    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict=model_config_dict,
    )

    # Cache params should be extracted and stored
    assert model._cache_control == "300s"
    assert model._cached_content == "cachedContents/abc123"

    # Cache params should not be in model_config_dict (passed to API)
    assert "cache_control" not in model.model_config_dict
    assert "cached_content" not in model.model_config_dict

    # Other params should remain
    assert model.model_config_dict["temperature"] == 0.5


@pytest.mark.model_backend
def test_gemini_model_has_cache_management_methods():
    r"""Test that GeminiModel has cache management methods."""
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict=model_config_dict,
    )

    # Verify cache management methods exist
    assert hasattr(model, 'create_cache')
    assert hasattr(model, 'list_caches')
    assert hasattr(model, 'get_cache')
    assert hasattr(model, 'update_cache')
    assert hasattr(model, 'delete_cache')
    assert hasattr(model, 'native_client')

    # Verify methods are callable
    assert callable(model.create_cache)
    assert callable(model.list_caches)
    assert callable(model.get_cache)
    assert callable(model.update_cache)
    assert callable(model.delete_cache)


@pytest.mark.model_backend
def test_gemini_model_cached_content_property():
    r"""Test that cached_content property can be set and cleared at runtime."""
    model_config_dict = GeminiConfig(
        temperature=0.5,
        cached_content="cachedContents/initial",
    ).as_dict()

    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict=model_config_dict,
    )

    # Initial cache should be extracted from config
    assert model.cached_content == "cachedContents/initial"
    assert "cached_content" not in model.model_config_dict

    # Can change cache at runtime via property
    model.cached_content = "cachedContents/updated"
    assert model.cached_content == "cachedContents/updated"

    # Can clear cache
    model.cached_content = None
    assert model.cached_content is None


@pytest.mark.model_backend
def test_gemini_cached_content_sent_via_nested_extra_body():
    r"""Test cached_content is injected under extra_body.google."""
    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict=GeminiConfig(
            cached_content="cachedContents/test-cache",
        ).as_dict(),
    )

    class DummyCompletions:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return {"id": "ok"}

    dummy_completions = DummyCompletions()
    model._client = type(  # type: ignore[assignment]
        "DummyClient",
        (),
        {
            "chat": type(
                "DummyChat",
                (),
                {"completions": dummy_completions},
            )()
        },
    )()

    model._request_chat_completion(
        messages=[{"role": "user", "content": "hi"}]
    )

    assert len(dummy_completions.calls) == 1
    assert (
        dummy_completions.calls[0]["extra_body"]["extra_body"]["google"][
            "cached_content"
        ]
        == "cachedContents/test-cache"
    )


@pytest.mark.model_backend
def test_gemini_cached_content_retries_without_cache_on_stale_error():
    r"""Test stale cached_content triggers a single retry without cache."""
    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict=GeminiConfig(
            cached_content="cachedContents/stale-cache",
        ).as_dict(),
    )

    class RetryCompletions:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                raise Exception("cached_content not found")
            return {"id": "ok"}

    retry_completions = RetryCompletions()
    model._client = type(  # type: ignore[assignment]
        "DummyClient",
        (),
        {
            "chat": type(
                "DummyChat",
                (),
                {"completions": retry_completions},
            )()
        },
    )()

    model._request_chat_completion(
        messages=[{"role": "user", "content": "hi"}]
    )

    assert len(retry_completions.calls) == 2
    assert (
        retry_completions.calls[0]["extra_body"]["extra_body"]["google"][
            "cached_content"
        ]
        == "cachedContents/stale-cache"
    )
    assert "extra_body" not in retry_completions.calls[1]
    assert model.cached_content is None


@pytest.mark.model_backend
def test_gemini_parse_path_applies_cached_content_and_retry():
    r"""Test parse path uses cache field and retries on stale cache."""
    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict=GeminiConfig(
            cached_content="cachedContents/stale-cache",
        ).as_dict(),
    )

    class DummySchema(BaseModel):
        value: str

    class RetryParseCompletions:
        def __init__(self):
            self.calls = []

        def parse(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                raise Exception("cached_content expired")
            return {"id": "ok"}

    retry_parse_completions = RetryParseCompletions()
    model._client = type(  # type: ignore[assignment]
        "DummyClient",
        (),
        {
            "beta": type(
                "DummyBeta",
                (),
                {
                    "chat": type(
                        "DummyChat",
                        (),
                        {"completions": retry_parse_completions},
                    )()
                },
            )()
        },
    )()

    model._request_parse(
        messages=[{"role": "user", "content": "hi"}],
        response_format=DummySchema,
    )

    assert len(retry_parse_completions.calls) == 2
    assert (
        retry_parse_completions.calls[0]["extra_body"]["extra_body"]["google"][
            "cached_content"
        ]
        == "cachedContents/stale-cache"
    )
    assert "extra_body" not in retry_parse_completions.calls[1]
    assert model.cached_content is None


@pytest.mark.model_backend
def test_gemini_cached_content_merges_with_existing_extra_body():
    r"""Test cached_content merges with existing nested extra_body fields."""
    model = GeminiModel(
        model_type=ModelType.GEMINI_2_0_FLASH,
        model_config_dict={
            "temperature": 0.2,
            "extra_body": {
                "extra_body": {
                    "google": {"thinking_config": {"type": "enabled"}}
                }
            },
            "cached_content": "cachedContents/merge-cache",
        },
    )

    request_config = model._prepare_request_config()
    assert request_config["extra_body"]["extra_body"]["google"][
        "thinking_config"
    ] == {"type": "enabled"}
    assert request_config["extra_body"]["extra_body"]["google"][
        "cached_content"
    ] == ("cachedContents/merge-cache")
