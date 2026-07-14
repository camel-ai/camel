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

import os
from unittest.mock import patch

import pytest

from camel.configs import DaoXEConfig
from camel.models import DaoXEModel
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "gpt-4o-mini",
        "claude-sonnet-4-20250514",
        "gemini-2.5-flash",
    ],
)
def test_daoxe_model_create(model_type: str):
    with patch.dict(os.environ, {"DAOXE_API_KEY": "test_key"}):
        model = DaoXEModel(model_type)
        assert str(model.model_type) == model_type


@pytest.mark.model_backend
def test_daoxe_model_create_with_config():
    config_dict = DaoXEConfig(
        temperature=0.5,
        top_p=1.0,
        max_tokens=100,
        stream=False,
    ).as_dict()

    with patch.dict(os.environ, {"DAOXE_API_KEY": "test_key"}):
        model = DaoXEModel(
            model_type="gpt-4o-mini",
            model_config_dict=config_dict,
        )
        assert str(model.model_type) == "gpt-4o-mini"
        assert model.model_config_dict == config_dict


@pytest.mark.model_backend
def test_daoxe_model_api_keys_required():
    assert hasattr(DaoXEModel.__init__, "__wrapped__")


@pytest.mark.model_backend
def test_daoxe_model_default_url(monkeypatch):
    monkeypatch.delenv("DAOXE_API_BASE_URL", raising=False)
    monkeypatch.setenv("DAOXE_API_KEY", "test_key")

    model = DaoXEModel("gpt-4o-mini")
    assert model._url == "https://daoxe.com/v1"


@pytest.mark.model_backend
def test_daoxe_model_custom_url(monkeypatch):
    custom_url = "https://custom.daoxe.endpoint/v1"
    monkeypatch.setenv("DAOXE_API_BASE_URL", custom_url)
    monkeypatch.setenv("DAOXE_API_KEY", "test_key")

    model = DaoXEModel("gpt-4o-mini")
    assert model._url == custom_url


@pytest.mark.model_backend
def test_daoxe_model_extends_openai_compatible():
    with patch.dict(os.environ, {"DAOXE_API_KEY": "test_key"}):
        model = DaoXEModel("gpt-4o-mini")
        assert isinstance(model, OpenAICompatibleModel)


@pytest.mark.model_backend
def test_daoxe_model_token_counter():
    with patch.dict(os.environ, {"DAOXE_API_KEY": "test_key"}):
        model = DaoXEModel("gpt-4o-mini")
        assert model.token_counter is not None
        assert isinstance(model.token_counter, OpenAITokenCounter)
        assert hasattr(model.token_counter, "count_tokens_from_messages")


@pytest.mark.model_backend
def test_daoxe_model_stream_property():
    with patch.dict(os.environ, {"DAOXE_API_KEY": "test_key"}):
        model = DaoXEModel("gpt-4o-mini")
        assert model.stream is False


@pytest.mark.model_backend
def test_daoxe_model_default_config():
    with patch.dict(os.environ, {"DAOXE_API_KEY": "test_key"}):
        model = DaoXEModel("gpt-4o-mini")
        assert model.model_config_dict == DaoXEConfig().as_dict()
