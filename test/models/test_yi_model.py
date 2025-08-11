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

from camel.configs import YiConfig
from camel.models import YiModel
from camel.types import ModelType


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.YI_LIGHTNING,
        ModelType.YI_LARGE,
        ModelType.YI_MEDIUM,
        ModelType.YI_LARGE_TURBO,
    ],
)
def test_yi_model(model_type: ModelType):
    model = YiModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == YiConfig().as_dict()
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)
