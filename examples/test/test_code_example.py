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
from mock import patch

import examples.code.role_playing
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def test_code_role_playing_example():
    with patch('time.sleep', return_value=None):
        examples.code.role_playing.main(
            ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.STUB,
            ),
            chat_turn_limit=2,
        )
