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
import re

import pytest

from camel.models import VolcanoModel
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
def test_volcano_model():
    # Using a string model type since Volcano supports various models
    model_type = "deepseek-r1-250120"
    model = VolcanoModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == {}
    assert isinstance(model.token_counter, OpenAITokenCounter)


@pytest.mark.model_backend
def test_volcano_model_unexpected_argument():
    model_type = "deepseek-r1-250120"
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Volcano model backend."
            )
        ),
    ):
        _ = VolcanoModel(model_type, model_config_dict)
