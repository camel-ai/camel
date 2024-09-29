# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import re

import pytest

from camel.configs import (
    ChatGPTConfig,
    OpenSourceConfig,
)
from camel.models import OpenSourceModel
from camel.models.model_type import ModelType
from camel.types import PredefinedModelType
from camel.utils import OpenSourceTokenCounter, check_server_running

MODEL_PATH_MAP = {
    PredefinedModelType.VICUNA: "lmsys/vicuna-7b-v1.5",
    PredefinedModelType.VICUNA_16K: "lmsys/vicuna-7b-v1.5-16k",
}
DEFAULT_SERVER_URL = "http://localhost:8000/v1"


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType(PredefinedModelType.VICUNA),
        ModelType(PredefinedModelType.VICUNA_16K),
    ],
)
def test_open_source_model(model_type):
    model_path = MODEL_PATH_MAP[model_type.type]
    model_name = model_path.split('/')[-1]
    model_config = OpenSourceConfig(
        model_path=model_path,
        server_url=DEFAULT_SERVER_URL,
    )
    model_config_dict = model_config.as_dict()
    model = OpenSourceModel(model_type, model_config_dict)

    assert model.model_type == model_type
    assert model.model_name == model_name
    assert model.server_url == model_config.server_url
    assert model.model_config_dict == model_config.api_params.as_dict()

    assert isinstance(model.token_counter, OpenSourceTokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", [PredefinedModelType.VICUNA])
@pytest.mark.skipif(
    not check_server_running(DEFAULT_SERVER_URL),
    reason="No server running LLM inference is provided.",
)
def test_open_source_model_run(model_type):
    model_path = MODEL_PATH_MAP[model_type]
    model_config = OpenSourceConfig(
        model_path=model_path,
        server_url=DEFAULT_SERVER_URL,
    )
    model_config_dict = model_config.as_dict()
    model = OpenSourceModel(model_type, model_config_dict)

    messages = [{"role": "user", "content": "Tell me a joke."}]
    response = model.run(messages)

    assert isinstance(response, dict)


@pytest.mark.model_backend
def test_open_source_model_close_source_model_type():
    model_type = ModelType(PredefinedModelType.GPT_4O_MINI)
    model_path = MODEL_PATH_MAP[PredefinedModelType.VICUNA]
    model_config = OpenSourceConfig(
        model_path=model_path,
        server_url=DEFAULT_SERVER_URL,
    )
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        ValueError,
        match=re.escape(
            ("Model `gpt-4o-mini` is not a supported" " open-source model.")
        ),
    ):
        _ = OpenSourceModel(model_type, model_config_dict)


@pytest.mark.model_backend
def test_open_source_model_mismatched_model_config():
    model_type = ModelType(PredefinedModelType.VICUNA)
    model_config = ChatGPTConfig()
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Invalid configuration for open-source model backend with "
                ":obj:`model_path` or :obj:`server_url` missing."
            )
        ),
    ):
        _ = OpenSourceModel(model_type, model_config_dict)


@pytest.mark.model_backend
def test_open_source_model_unexpected_argument():
    model_type = PredefinedModelType.VICUNA
    model_path = MODEL_PATH_MAP[PredefinedModelType.VICUNA]
    model_config = OpenSourceConfig(
        model_path=model_path,
        server_url=DEFAULT_SERVER_URL,
        api_params=ChatGPTConfig(),
    )
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        TypeError,
        match=re.escape(
            ("__init__() got an unexpected keyword argument 'unexpected_arg'")
        ),
    ):
        _ = OpenSourceModel(
            model_type, model_config_dict, unexpected_arg="unexpected_arg"
        )


@pytest.mark.model_backend
def test_open_source_model_invalid_model_path():
    model_type = ModelType(PredefinedModelType.VICUNA)
    model_path = "vicuna-7b-v1.5"
    model_config = OpenSourceConfig(
        model_path=model_path,
        server_url=DEFAULT_SERVER_URL,
    )
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Invalid `model_path` (vicuna-7b-v1.5) is provided. "
                "Tokenizer loading failed."
            )
        ),
    ):
        model = OpenSourceModel(model_type, model_config_dict)
        _ = model.token_counter


@pytest.mark.model_backend
def test_open_source_model_unmatched_model_path():
    model_type = ModelType(PredefinedModelType.LLAMA_2)
    model_path = MODEL_PATH_MAP[PredefinedModelType.VICUNA]
    model_config = OpenSourceConfig(
        model_path=model_path,
        server_url=DEFAULT_SERVER_URL,
    )
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        ValueError,
        match=(
            f"Model name `vicuna-7b-v1.5` does not match model type "
            f"`{model_type.value}`."
        ),
    ):
        _ = OpenSourceModel(model_type, model_config_dict)


@pytest.mark.model_backend
def test_open_source_model_missing_model_path():
    model_type = ModelType(PredefinedModelType.VICUNA)
    model_config = OpenSourceConfig(
        model_path="",
        server_url=DEFAULT_SERVER_URL,
    )
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        ValueError, match=("Path to open-source model is not provided.")
    ):
        _ = OpenSourceModel(model_type, model_config_dict)


@pytest.mark.model_backend
def test_open_source_model_missing_server_url():
    model_type = ModelType(PredefinedModelType.VICUNA)
    model_path = MODEL_PATH_MAP[PredefinedModelType.VICUNA]
    model_config = OpenSourceConfig(model_path=model_path, server_url="")
    model_config_dict = model_config.as_dict()

    with pytest.raises(
        ValueError,
        match=("URL to server running open-source LLM is not provided."),
    ):
        _ = OpenSourceModel(model_type, model_config_dict)
