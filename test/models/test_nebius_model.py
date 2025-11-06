# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import pytest

from camel.configs import NebiusConfig
from camel.models import NebiusModel
from camel.types import ModelType


@pytest.mark.model_backend
class TestNebiusModel:
    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.NEBIUS_GPT_OSS_120B,
            ModelType.NEBIUS_GPT_OSS_20B,
            ModelType.NEBIUS_GLM_4_5,
        ],
    )
    def test_nebius_model_create(self, model_type: ModelType):
        model = NebiusModel(model_type)
        assert model.model_type == model_type

    def test_nebius_model_create_with_config(self):
        config_dict = NebiusConfig(
            temperature=0.5,
            top_p=1.0,
            max_tokens=100,
        ).as_dict()

        model = NebiusModel(
            model_type=ModelType.NEBIUS_GPT_OSS_120B,
            model_config_dict=config_dict,
        )

        assert model.model_type == ModelType.NEBIUS_GPT_OSS_120B
        assert model.model_config_dict == config_dict

    def test_nebius_model_api_keys_required(self):
        # Test that the api_keys_required decorator is applied
        assert hasattr(NebiusModel.__init__, "__wrapped__")

    def test_nebius_model_default_url(self, monkeypatch):
        # Test default URL when no environment variable is set
        monkeypatch.delenv("NEBIUS_API_BASE_URL", raising=False)
        monkeypatch.setenv("NEBIUS_API_KEY", "test_key")

        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        assert model._url == "https://api.studio.nebius.com/v1"

    def test_nebius_model_custom_url(self, monkeypatch):
        # Test custom URL from environment variable
        custom_url = "https://custom.nebius.endpoint/v1"
        monkeypatch.setenv("NEBIUS_API_BASE_URL", custom_url)
        monkeypatch.setenv("NEBIUS_API_KEY", "test_key")

        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        assert model._url == custom_url

    def test_nebius_model_extends_openai_compatible(self):
        # Test that NebiusModel inherits from OpenAICompatibleModel
        from camel.models.openai_compatible_model import OpenAICompatibleModel

        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        assert isinstance(model, OpenAICompatibleModel)

    def test_nebius_model_token_counter(self):
        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        # Should use the default OpenAI token counter
        assert model.token_counter is not None
        assert hasattr(model.token_counter, "count_tokens_from_messages")

    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.NEBIUS_GPT_OSS_120B,
            ModelType.NEBIUS_GPT_OSS_20B,
            ModelType.NEBIUS_GLM_4_5,
            ModelType.NEBIUS_DEEPSEEK_V3,
            ModelType.NEBIUS_DEEPSEEK_R1,
            ModelType.NEBIUS_LLAMA_3_1_70B,
            ModelType.NEBIUS_MISTRAL_7B_INSTRUCT,
        ],
    )
    def test_nebius_model_types_available(self, model_type: ModelType):
        # Test that all defined Nebius model types are recognized
        assert model_type.is_nebius
        model = NebiusModel(model_type)
        assert isinstance(model.model_type, ModelType)
