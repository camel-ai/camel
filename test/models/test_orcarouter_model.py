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

from camel.configs import OrcaRouterConfig
from camel.models import OrcaRouterModel
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.ORCAROUTER_AUTO,
        ModelType.ORCAROUTER_GPT_5,
        ModelType.ORCAROUTER_CLAUDE_OPUS_4_7,
        ModelType.ORCAROUTER_GEMINI_3_FLASH_PREVIEW,
        ModelType.ORCAROUTER_GROK_4_3,
    ],
)
def test_orcarouter_predefined_models(model_type: ModelType):
    model = OrcaRouterModel(model_type, api_key="test-key")
    assert model.model_type == model_type
    assert model.model_config_dict == OrcaRouterConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    # Predefined entries should have a sensible token limit (not fall back
    # to the 999_999_999 unknown-model warning).
    assert model.model_type.token_limit < 999_999_999
    # Predefined entries should report as OrcaRouter-served and as
    # supporting native tool calling at the ModelType level.
    assert model.model_type.is_orcarouter is True
    assert model.model_type.support_native_tool_calling is True


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "qwen/qwen3.5-flash",
        "deepseek/deepseek-chat",
        "grok/grok-4-0709",
        "minimax/minimax-m2.7",
    ],
)
def test_orcarouter_freeform_string_models(model_type: str):
    """Non-predefined model ids should work via free-form string."""
    model = OrcaRouterModel(model_type, api_key="test-key")
    assert model.model_type == model_type
    assert model.model_config_dict == OrcaRouterConfig().as_dict()


@pytest.mark.model_backend
def test_orcarouter_model_stream_property():
    model = OrcaRouterModel(ModelType.ORCAROUTER_AUTO, api_key="test-key")
    assert model.stream is False


@pytest.mark.model_backend
def test_orcarouter_model_default_url():
    model = OrcaRouterModel(ModelType.ORCAROUTER_AUTO, api_key="test-key")
    assert str(model._url) == "https://api.orcarouter.ai/v1"


@pytest.mark.model_backend
def test_orcarouter_config_extra_body():
    config = OrcaRouterConfig(
        extra_body={
            "models": ["openai/gpt-4o-mini", "openai/gpt-4o"],
            "route": "fallback",
        }
    ).as_dict()

    assert config["extra_body"] == {
        "models": ["openai/gpt-4o-mini", "openai/gpt-4o"],
        "route": "fallback",
    }


@pytest.mark.model_backend
def test_orcarouter_model_missing_api_key(monkeypatch):
    monkeypatch.delenv("ORCAROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ORCAROUTER_API_KEY"):
        OrcaRouterModel(ModelType.ORCAROUTER_AUTO, api_key=None)


@pytest.mark.model_backend
def test_orcarouter_platform_enum():
    """`from_name` should resolve `'orcarouter'` to the dedicated platform."""
    assert ModelPlatformType.from_name("orcarouter") is (
        ModelPlatformType.ORCAROUTER
    )
    assert ModelPlatformType.ORCAROUTER.is_orcarouter is True
