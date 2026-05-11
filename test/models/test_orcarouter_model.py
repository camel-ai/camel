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
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "gpt-4o",
        "gpt-4o-mini",
        "claude-opus-4-6",
        "deepseek-chat",
    ],
)
def test_orcarouter_model(model_type: str):
    model = OrcaRouterModel(model_type, api_key="test-key")
    assert model.model_type == model_type
    assert model.model_config_dict == OrcaRouterConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)


@pytest.mark.model_backend
def test_orcarouter_model_stream_property():
    model = OrcaRouterModel("gpt-4o", api_key="test-key")
    assert model.stream is False


@pytest.mark.model_backend
def test_orcarouter_model_default_url():
    model = OrcaRouterModel("gpt-4o", api_key="test-key")
    assert str(model._url) == "https://api.orcarouter.ai/v1"


@pytest.mark.model_backend
def test_orcarouter_model_missing_api_key(monkeypatch):
    monkeypatch.delenv("ORCAROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ORCAROUTER_API_KEY"):
        OrcaRouterModel("gpt-4o", api_key=None)
