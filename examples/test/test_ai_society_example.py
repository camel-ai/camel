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

import examples.ai_society.role_playing
import examples.function_call.role_playing_with_function
from camel.typing import ModelType


@pytest.mark.slow
def test_ai_society_role_playing_example():
    examples.ai_society.role_playing.main(ModelType.STUB)


@pytest.mark.slow
def test_role_playing_with_function_example():
    examples.function_call.role_playing_with_function.main(ModelType.STUB)
