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

from camel.configs import NexaConfig
from camel.models import NexaModel
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    ["llama3.2"],
)
def test_nexa_model(model_type: str):
    model = NexaModel(model_type, url="http://localhost:8000/v1")
    assert model.model_type == model_type
    assert model.model_config_dict == NexaConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.token_limit, int)


@pytest.mark.model_backend
def test_nexa_model_unexpected_argument():
    model_type = "llama3.2"
    model_config_dict = {"unexpected_arg": "value"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `unexpected_arg` is "
                "input into Nexa model backend."
            )
        ),
    ):
        _ = NexaModel(model_type, model_config_dict, api_key="nexa_api_key")
