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

from camel.prompts import PromptTemplateGenerator, TextPrompt
from camel.types import RoleType, TaskType


@pytest.mark.parametrize(
    'task_role_tuple',
    [
        (TaskType.AI_SOCIETY, RoleType.ASSISTANT),
        (TaskType.AI_SOCIETY, RoleType.USER),
        (TaskType.CODE, RoleType.ASSISTANT),
        (TaskType.CODE, RoleType.USER),
        (TaskType.MISALIGNMENT, RoleType.ASSISTANT),
        (TaskType.MISALIGNMENT, RoleType.USER),
        (TaskType.TRANSLATION, RoleType.ASSISTANT),
    ],
)
def test_get_system_prompt(task_role_tuple):
    task_type, role_type = task_role_tuple
    prompt_template = PromptTemplateGenerator().get_system_prompt(
        task_type, role_type
    )
    assert isinstance(prompt_template, TextPrompt)


def test_get_system_prompt_default():
    prompt_template = PromptTemplateGenerator().get_system_prompt(
        TaskType.AI_SOCIETY, RoleType.DEFAULT
    )
    assert isinstance(prompt_template, TextPrompt)


@pytest.mark.parametrize(
    'task_type', [TaskType.AI_SOCIETY, TaskType.CODE, TaskType.MISALIGNMENT]
)
def test_get_generate_tasks_prompt(task_type):
    prompt_template = PromptTemplateGenerator().get_generate_tasks_prompt(
        task_type
    )
    assert isinstance(prompt_template, TextPrompt)


@pytest.mark.parametrize(
    'task_type', [TaskType.AI_SOCIETY, TaskType.CODE, TaskType.MISALIGNMENT]
)
def test_get_task_specify_prompt(task_type):
    prompt_template = PromptTemplateGenerator().get_task_specify_prompt(
        task_type
    )
    assert isinstance(prompt_template, TextPrompt)
