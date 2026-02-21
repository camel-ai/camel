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
import pytest
from mock import patch

import examples.role_description.role_generation
import examples.role_description.role_playing_with_role_description
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


@pytest.fixture
def model_gpt():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not found")
    return ModelFactory.create(
        ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
    )


@pytest.fixture
def model_stub():
    return ModelFactory.create(
        ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )


def test_role_generation_example(model_gpt):
    with patch('time.sleep', return_value=None):
        examples.role_description.role_generation.main(model_gpt)


def test_role_playing_with_role_description_example(model_gpt, model_stub):
    with patch('time.sleep', return_value=None):
        examples.role_description.role_playing_with_role_description.main(
            model_gpt, model_stub, chat_turn_limit=2
        )
