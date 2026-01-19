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

from camel.configs import AnthropicConfig
from camel.models import AnthropicModel
from camel.types import ModelType
from camel.utils import AnthropicTokenCounter, BaseTokenCounter

# Skip all tests in this module if the anthropic package is not available.
pytest.importorskip("anthropic", reason="anthropic package is required")


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.CLAUDE_INSTANT_1_2,
        ModelType.CLAUDE_2_0,
        ModelType.CLAUDE_2_1,
        ModelType.CLAUDE_3_OPUS,
        ModelType.CLAUDE_3_SONNET,
        ModelType.CLAUDE_3_HAIKU,
        ModelType.CLAUDE_3_5_SONNET,
        ModelType.CLAUDE_3_5_HAIKU,
        ModelType.CLAUDE_3_7_SONNET,
        ModelType.CLAUDE_SONNET_4_5,
        ModelType.CLAUDE_OPUS_4_5,
        ModelType.CLAUDE_SONNET_4,
        ModelType.CLAUDE_OPUS_4,
        ModelType.CLAUDE_OPUS_4_1,
    ],
)
def test_anthropic_model(model_type: ModelType):
    model = AnthropicModel(model_type, api_key="dummy_api_key")
    assert model.model_type == model_type
    assert model.model_config_dict == AnthropicConfig().as_dict()
    assert isinstance(model.token_counter, AnthropicTokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


def test_anthropic_model_uses_provided_token_counter():
    class DummyTokenCounter(BaseTokenCounter):
        def count_tokens_from_messages(self, messages):
            return 42

        def encode(self, text: str):
            return [1, 2, 3]

        def decode(self, token_ids):
            return "decoded"

    token_counter = DummyTokenCounter()
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict=AnthropicConfig().as_dict(),
        api_key="dummy_api_key",
        token_counter=token_counter,
    )

    assert model.token_counter is token_counter


def test_anthropic_model_cache_control_valid_and_invalid():
    # Valid cache_control values should configure _cache_control_config
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
        cache_control="5m",
    )
    assert model._cache_control_config == {
        "type": "ephemeral",
        "ttl": "5m",
    }

    # Invalid cache_control should raise ValueError
    with pytest.raises(ValueError):
        AnthropicModel(
            ModelType.CLAUDE_3_HAIKU,
            api_key="dummy_api_key",
            cache_control="10m",
        )


def test_anthropic_model_stream_property():
    model_stream = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict={"stream": True},
        api_key="dummy_api_key",
    )
    assert model_stream.stream is True

    model_non_stream = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict={"stream": False},
        api_key="dummy_api_key",
    )
    assert model_non_stream.stream is False
