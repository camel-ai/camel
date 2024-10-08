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
from mock import patch

import examples.ai_society.role_playing
import examples.function_call.role_playing_with_functions
import examples.models.role_playing_with_open_source_model
from camel.models import ModelFactory
from camel.types import ModelPlatformType, PredefinedModelType

test_model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=PredefinedModelType.STUB,
)


def test_ai_society_role_playing_example():
    with patch('time.sleep', return_value=None):
        examples.ai_society.role_playing.main(
            model=test_model, chat_turn_limit=2
        )


def test_role_playing_with_function_example():
    with patch('time.sleep', return_value=None):
        examples.function_call.role_playing_with_functions.main(
            chat_turn_limit=2
        )


def test_role_playing_with_open_source_model():
    with patch('time.sleep', return_value=None):
        examples.models.role_playing_with_open_source_model.main(
            chat_turn_limit=2
        )
