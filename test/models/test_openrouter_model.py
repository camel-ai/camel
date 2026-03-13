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

from camel.configs import OpenRouterConfig
from camel.models import OpenRouterModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.OPENROUTER_LLAMA_3_1_405B,
        ModelType.OPENROUTER_LLAMA_3_1_70B,
        ModelType.OPENROUTER_OLYMPICODER_7B,
        ModelType.OPENROUTER_HORIZON_ALPHA,
    ],
)
def test_openrouter_model(model_type: ModelType):
    model = OpenRouterModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == OpenRouterConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_openrouter_model_stream_property():
    model = OpenRouterModel(ModelType.OPENROUTER_LLAMA_3_1_70B)
    assert model.stream is False


@pytest.mark.model_backend
def test_openrouter_model_app_attribution_headers():
    r"""Test that OpenRouter App Attribution headers are properly set."""
    model = OpenRouterModel(ModelType.OPENROUTER_LLAMA_3_1_70B)

    # Check that the client has the default headers set
    assert hasattr(model._client, 'default_headers')
    headers = model._client.default_headers

    # Verify App Attribution headers are present
    assert 'HTTP-Referer' in headers
    assert headers['HTTP-Referer'] == 'https://www.camel-ai.org/'
    assert 'X-Title' in headers
    assert headers['X-Title'] == 'CAMEL-AI'


@pytest.mark.model_backend
def test_openrouter_model_preserves_custom_headers():
    r"""Test that custom headers are preserved along with attribution."""
    custom_headers = {'Custom-Header': 'custom-value'}
    model = OpenRouterModel(
        ModelType.OPENROUTER_LLAMA_3_1_70B,
        default_headers=custom_headers,
    )

    headers = model._client.default_headers

    # Verify both custom and attribution headers are present
    assert 'Custom-Header' in headers
    assert headers['Custom-Header'] == 'custom-value'
    assert 'HTTP-Referer' in headers
    assert headers['HTTP-Referer'] == 'https://www.camel-ai.org/'
    assert 'X-Title' in headers
    assert headers['X-Title'] == 'CAMEL-AI'


@pytest.mark.model_backend
def test_openrouter_model_custom_attribution_headers():
    r"""Test that custom attribution header values can be provided."""
    model = OpenRouterModel(
        ModelType.OPENROUTER_LLAMA_3_1_70B,
        app_referer='https://custom-site.com/',
        app_title='Custom-App',
    )

    headers = model._client.default_headers

    # Verify custom attribution headers are used
    assert 'HTTP-Referer' in headers
    assert headers['HTTP-Referer'] == 'https://custom-site.com/'
    assert 'X-Title' in headers
    assert headers['X-Title'] == 'Custom-App'


@pytest.mark.model_backend
def test_openrouter_model_disable_attribution_headers():
    r"""Test that attribution headers can be disabled."""
    model = OpenRouterModel(
        ModelType.OPENROUTER_LLAMA_3_1_70B,
        app_referer=None,
        app_title=None,
    )

    headers = model._client.default_headers

    # Verify attribution headers are not present
    assert 'HTTP-Referer' not in headers
    assert 'X-Title' not in headers


@pytest.mark.model_backend
def test_openrouter_model_partial_attribution_headers():
    r"""Test that individual attribution headers can be customized or disabled."""
    model = OpenRouterModel(
        ModelType.OPENROUTER_LLAMA_3_1_70B,
        app_referer='https://my-custom-site.com/',
        app_title=None,
    )

    headers = model._client.default_headers

    # Verify only HTTP-Referer is set with custom value
    assert 'HTTP-Referer' in headers
    assert headers['HTTP-Referer'] == 'https://my-custom-site.com/'
    assert 'X-Title' not in headers
