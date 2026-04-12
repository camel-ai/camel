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
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from camel.types import ModelType, OpenAIVisionDetailType
from camel.utils import AnthropicTokenCounter, OpenAITokenCounter

pytest.importorskip("anthropic", reason="anthropic package is required")


@pytest.mark.parametrize(
    "width,height,detail,token_cost",
    [
        (1024, 1024, OpenAIVisionDetailType.HIGH, 765),
        (1024, 1024, OpenAIVisionDetailType.AUTO, 765),
        (2048, 4096, OpenAIVisionDetailType.HIGH, 1105),
        (2048, 4096, OpenAIVisionDetailType.LOW, 85),
    ],
)
def test_openai_count_token_from_image(
    width: int, height: int, detail: OpenAIVisionDetailType, token_cost: int
):
    image = Image.new("RGB", (width, height), "black")
    assert (
        OpenAITokenCounter(ModelType.GPT_4O_MINI)._count_tokens_from_image(
            image, detail
        )
        == token_cost
    )


def test_anthropic_token_counter_uses_remote_count_for_official_url():
    messages = [{"role": "user", "content": "Hello"}]

    mock_client = MagicMock()
    mock_client.messages.count_tokens.return_value.input_tokens = 42

    with patch("anthropic.Anthropic", return_value=mock_client):
        counter = AnthropicTokenCounter(
            model="claude-sonnet-4-5",
            api_key="dummy_api_key",
            base_url="https://api.anthropic.com",
        )
        assert counter.count_tokens_from_messages(messages) == 42

    mock_client.messages.count_tokens.assert_called_once()


def test_anthropic_token_counter_uses_local_fallback_for_custom_url():
    messages = [{"role": "user", "content": "Hello"}]

    mock_client = MagicMock()

    with patch("anthropic.Anthropic", return_value=mock_client):
        counter = AnthropicTokenCounter(
            model="claude-sonnet-4-5",
            api_key="dummy_api_key",
            base_url="https://zenmux.ai/api/anthropic",
        )

    with patch.object(
        OpenAITokenCounter,
        "count_tokens_from_messages",
        return_value=17,
    ) as mock_local_count:
        assert counter.count_tokens_from_messages(messages) == 17

    mock_local_count.assert_called_once_with(messages)
    mock_client.messages.count_tokens.assert_not_called()
