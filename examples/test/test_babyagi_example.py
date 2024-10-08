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
import pytest
from mock import patch

import examples.ai_society.babyagi_playing
from camel.models import ModelFactory
from camel.types import ModelPlatformType, PredefinedModelType

parametrize = pytest.mark.parametrize(
    'model',
    [
        ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=PredefinedModelType.STUB,
        ),
        pytest.param(None, marks=pytest.mark.model_backend),
    ],
)


@parametrize
def test_ai_society_babyagi_playing_example(model):
    with patch('time.sleep', return_value=None):
        examples.ai_society.babyagi_playing.main(
            model=model, chat_turn_limit=2
        )
