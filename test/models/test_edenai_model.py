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

from camel.configs import EdenAIConfig
from camel.models import EdenAIModel
from camel.types import ModelPlatformType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4-5",
        "mistral/mistral-large-latest",
    ],
)
def test_edenai_model(model_type: str):
    # Eden AI model ids are vendor-prefixed free-form strings.
    model = EdenAIModel(model_type, api_key="test-key")
    assert model.model_type == model_type
    assert model.model_config_dict == EdenAIConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert str(model.model_type) == model_type


@pytest.mark.model_backend
def test_edenai_model_stream_property():
    model = EdenAIModel("openai/gpt-4o-mini", api_key="test-key")
    assert model.stream is False


@pytest.mark.model_backend
def test_edenai_model_default_url():
    model = EdenAIModel("openai/gpt-4o-mini", api_key="test-key")
    assert str(model._url) == "https://api.edenai.run/v3"


@pytest.mark.model_backend
def test_edenai_config_extra_body():
    config = EdenAIConfig(extra_body={"foo": "bar"}).as_dict()
    assert config["extra_body"] == {"foo": "bar"}


@pytest.mark.model_backend
def test_edenai_model_missing_api_key(monkeypatch):
    monkeypatch.delenv("EDENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EDENAI_API_KEY"):
        EdenAIModel("openai/gpt-4o-mini", api_key=None)


@pytest.mark.model_backend
def test_edenai_platform_enum():
    """`from_name` should resolve `'edenai'` to the dedicated platform."""
    assert ModelPlatformType.from_name("edenai") is ModelPlatformType.EDENAI
    assert ModelPlatformType.EDENAI.is_edenai is True
