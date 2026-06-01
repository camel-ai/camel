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


from camel.models import EvolinkModel
from camel.types import ModelPlatformType


def test_evolink_model_defaults(monkeypatch):
    monkeypatch.setenv("EVOLINK_API_KEY", "test-key")
    monkeypatch.delenv("EVOLINK_API_BASE_URL", raising=False)

    model = EvolinkModel(model_type="gpt-5.2")

    assert str(model.model_type) == "gpt-5.2"
    assert model._url == "https://direct.evolink.ai/v1"
    assert model._api_key == "test-key"
    assert model.model_config_dict == {}


def test_evolink_model_explicit_args(monkeypatch):
    monkeypatch.delenv("EVOLINK_API_KEY", raising=False)

    model = EvolinkModel(
        model_type="deepseek-v4-pro",
        api_key="explicit-key",
        url="https://custom.example.com/v1",
        model_config_dict={"temperature": 0.0},
    )

    assert str(model.model_type) == "deepseek-v4-pro"
    assert model._api_key == "explicit-key"
    assert model._url == "https://custom.example.com/v1"
    assert model.model_config_dict == {"temperature": 0.0}


def test_evolink_model_base_url_from_env(monkeypatch):
    monkeypatch.setenv("EVOLINK_API_KEY", "test-key")
    monkeypatch.setenv("EVOLINK_API_BASE_URL", "https://env.example.com/v1")

    model = EvolinkModel(model_type="gpt-5.2")

    assert model._url == "https://env.example.com/v1"


def test_evolink_platform_flag():
    assert ModelPlatformType.EVOLINK.is_evolink
    assert ModelPlatformType("evolink") is ModelPlatformType.EVOLINK
