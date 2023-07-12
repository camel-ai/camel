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
from camel.prompts import TextPrompt
from camel.typing import RoleType
from camel.prompts.game import GamePromptTemplateDict


def test_game_prompt_template_dict():
    template_dict = GamePromptTemplateDict()

    # Test if the prompts are of the correct type
    assert isinstance(template_dict.BEGIN_PROMPT, TextPrompt)
    assert isinstance(template_dict.ROUND_PROMPT, TextPrompt)

    # Test if the prompts are correctly added to the dictionary

    assert template_dict["begin_prompt"] == template_dict.BEGIN_PROMPT
    assert template_dict[RoleType.PLAYER] == template_dict.ROUND_PROMPT
