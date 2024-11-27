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
from camel.prompts import AISocietyPromptTemplateDict, TextPrompt
from camel.types import RoleType


def test_ai_society_prompt_template_dict():
    template_dict = AISocietyPromptTemplateDict()

    # Test if the prompts are of the correct type
    assert isinstance(template_dict.GENERATE_ASSISTANTS, TextPrompt)
    assert isinstance(template_dict.GENERATE_USERS, TextPrompt)
    assert isinstance(template_dict.GENERATE_TASKS, TextPrompt)
    assert isinstance(template_dict.TASK_SPECIFY_PROMPT, TextPrompt)
    assert isinstance(template_dict.ASSISTANT_PROMPT, TextPrompt)
    assert isinstance(template_dict.USER_PROMPT, TextPrompt)

    # Test if the prompts are correctly added to the dictionary
    assert (
        template_dict['generate_assistants']
        == template_dict.GENERATE_ASSISTANTS
    )
    assert template_dict['generate_users'] == template_dict.GENERATE_USERS
    assert template_dict['generate_tasks'] == template_dict.GENERATE_TASKS
    assert (
        template_dict['task_specify_prompt']
        == template_dict.TASK_SPECIFY_PROMPT
    )
    assert template_dict[RoleType.ASSISTANT] == template_dict.ASSISTANT_PROMPT
    assert template_dict[RoleType.USER] == template_dict.USER_PROMPT
