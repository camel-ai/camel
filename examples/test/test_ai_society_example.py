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
import examples.ai_society.role_playing_by_chain_of_thought
import examples.function_call.role_playing_with_function
import examples.open_source_models.role_playing_with_open_source_model
from camel.types import ModelType


def test_ai_society_role_playing_example():
    with patch('time.sleep', return_value=None):
        examples.ai_society.role_playing.main(ModelType.STUB,
                                              chat_turn_limit=2)


def test_ai_society_role_playing_by_chain_of_thought_example():
    with patch('time.sleep', return_value=None):
        examples.ai_society.role_playing_by_chain_of_thought.main(
            ModelType.STUB, chat_turn_limit=2)


def test_role_playing_with_function_example():
    with patch('time.sleep', return_value=None):
        examples.function_call.role_playing_with_function.main(
            ModelType.STUB, chat_turn_limit=2)


def test_role_playing_with_open_source_model():
    with patch('time.sleep', return_value=None):
        examples.open_source_models.role_playing_with_open_source_model.main(
            ModelType.STUB, chat_turn_limit=2)
