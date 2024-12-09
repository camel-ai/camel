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
from camel.generators import (
    AISocietyTaskPromptGenerator,
    RoleNameGenerator,
    SystemMessageGenerator,
)
from camel.types import RoleType, TaskType


def test_system_message_generator():
    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
    sys_msg_generator.from_dict(
        dict(assistant_role="doctor"),
        role_tuple=("doctor", RoleType.ASSISTANT),
    )
    sys_msg_generator.from_dict(
        dict(user_role="doctor"), role_tuple=("doctor", RoleType.USER)
    )

    sys_msg_generator.from_dicts(
        [dict(assistant_role="doctor", user_role="doctor")] * 2,
        role_tuples=[
            ("chatbot", RoleType.ASSISTANT),
            ("doctor", RoleType.USER),
        ],
    )

    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.AI_SOCIETY)
    sys_msg_generator.from_dicts(
        [
            dict(
                assistant_role="chatbot",
                user_role="doctor",
                task="Analyze a patient's medical report",
            )
        ]
        * 2,
        role_tuples=[
            ("chatbot", RoleType.ASSISTANT),
            ("doctor", RoleType.USER),
        ],
    )


def test_role_name_generator():
    role_name_generator = RoleNameGenerator().from_role_files()
    role_tuple = next(role_name_generator)
    assert isinstance(role_tuple, tuple)


def test_task_prompt_generator():
    role_name_generator = RoleNameGenerator().from_role_files()
    task_prompt, role_names = next(
        AISocietyTaskPromptGenerator().from_role_generator(role_name_generator)
    )
    assert isinstance(task_prompt, str)
    assert isinstance(role_names, tuple)
    for role_name in role_names:
        assert isinstance(role_name, str)

    task_prompt, role_names = next(
        AISocietyTaskPromptGenerator().from_role_files()
    )
    assert isinstance(task_prompt, str)
    assert isinstance(role_names, tuple)
    for role_name in role_names:
        assert isinstance(role_name, str)
