# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
import re

import pytest

from camel.configs import (
    SambaCloudAPIConfig,
)
from camel.models import SambaModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "llama3-70b",
    ],
)
def test_samba_model(model_type: ModelType):
    model = SambaModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == SambaCloudAPIConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)


@pytest.mark.model_backend
def test_samba_model_unexpected_argument():
    model_type = "llama3-70b"
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into SambaCloud API."
            )
        ),
    ):
        _ = SambaModel(model_type, model_config_dict)
