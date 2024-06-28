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

from camel.models import ModelFactory
from camel.types import ModelPlatformType


@pytest.mark.model_backend
def test_open_source_model_invalid_url():
    model_platform = ModelPlatformType.FASTCHAT
    model_type = ""
    model_config_dict = {
        "model_name": "Qwen",
        "api_params": {"temperature": 0.4},
    }

    with pytest.raises(
        ValueError,
        match=re.escape("URL to server running fastchat LLM is not provided."),
    ):
        _ = ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=model_config_dict,
        )


@pytest.mark.model_backend
def test_open_source_model_invalid_model_name():
    model_platform = ModelPlatformType.FASTCHAT
    model_type = ""
    model_config_dict = {
        "api_params": {"temperature": 0.4},
    }

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Invalid configuration for fastchat model backend with "
                ":obj:`model_name` missing."
            )
        ),
    ):
        _ = ModelFactory.create(
            url="http://127.0.0.1:8000/v1",
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=model_config_dict,
        )
