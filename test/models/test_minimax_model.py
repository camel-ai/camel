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

from camel.configs import MinimaxConfig
from camel.models import MinimaxModel
from camel.types import ModelType


@pytest.mark.model_backend
class TestMinimaxModel:
    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.MINIMAX_M2,
            ModelType.MINIMAX_M2_STABLE,
        ],
    )
    def test_minimax_m2_model_create(self, model_type: ModelType, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test_key")
        model = MinimaxModel(model_type)
        assert model.model_type == model_type

    def test_minimax_m2_model_create_with_config(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test_key")
        config_dict = MinimaxConfig(
            temperature=0.5,
            top_p=1.0,
            max_tokens=100,
        ).as_dict()

        model = MinimaxModel(
            model_type=ModelType.MINIMAX_M2,
            model_config_dict=config_dict,
        )

        assert model.model_type == ModelType.MINIMAX_M2
        assert model.model_config_dict == config_dict

    def test_minimax_m2_model_api_keys_required(self):
        # Test that the api_keys_required decorator is applied
        assert hasattr(MinimaxModel.__init__, "__wrapped__")

    def test_minimax_m2_model_default_url(self, monkeypatch):
        # Test default URL when no environment variable is set
        monkeypatch.delenv("MINIMAX_API_BASE_URL", raising=False)
        monkeypatch.setenv("MINIMAX_API_KEY", "test_key")

        model = MinimaxModel(ModelType.MINIMAX_M2)
        assert model._url == "https://api.minimaxi.com/v1"

    def test_minimax_m2_model_custom_url(self, monkeypatch):
        # Test custom URL from environment variable
        custom_url = "https://custom.minimax.endpoint/v1"
        monkeypatch.setenv("MINIMAX_API_BASE_URL", custom_url)
        monkeypatch.setenv("MINIMAX_API_KEY", "test_key")

        model = MinimaxModel(ModelType.MINIMAX_M2)
        assert model._url == custom_url

    def test_minimax_m2_model_extends_openai_compatible(self, monkeypatch):
        # Test that MinimaxModel inherits from OpenAICompatibleModel
        monkeypatch.setenv("MINIMAX_API_KEY", "test_key")
        from camel.models.openai_compatible_model import OpenAICompatibleModel

        model = MinimaxModel(ModelType.MINIMAX_M2)
        assert isinstance(model, OpenAICompatibleModel)

    def test_minimax_m2_model_token_counter(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test_key")
        model = MinimaxModel(ModelType.MINIMAX_M2)
        # Should use the default OpenAI token counter
        assert model.token_counter is not None
        assert hasattr(model.token_counter, "count_tokens_from_messages")

    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.MINIMAX_M2,
            ModelType.MINIMAX_M2_STABLE,
        ],
    )
    def test_minimax_m2_model_types_available(self, model_type: ModelType):
        # Test that all defined Minimax M2 model types are recognized
        assert model_type.is_minimax
        model = MinimaxModel(model_type)
        assert isinstance(model.model_type, ModelType)
