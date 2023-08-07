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
from camel.agents.role_assignment import RoleAssignmentAgent
from camel.configs import ChatGPTConfig
from camel.societies import RolePlaying
from camel.typing import ModelType

AI_ASSISTANT_ROLE_INDEX = 0
AI_USER_ROLE_INDEX = 1


def test_ai_society_with_role_generation():
    model_type = ModelType.GPT_3_5_TURBO
    task_prompt = "Develop a trading bot for the stock market."

    model_config_description = ChatGPTConfig()
    role_description_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)

    role_names, role_description_dict, _, _ = (
        role_description_agent.run_role_with_description(
            num_roles=2, task_prompt=task_prompt))

    ai_assistant_role = role_names[AI_ASSISTANT_ROLE_INDEX]
    ai_user_role = role_names[AI_USER_ROLE_INDEX]

    role_play_session = RolePlaying(
        task_prompt=task_prompt,
        with_task_specify=True,
        assistant_role_name=ai_assistant_role,
        user_role_name=ai_user_role,
        assistant_agent_kwargs=dict(
            model=model_type,
            role_description=role_description_dict[ai_assistant_role]),
        user_agent_kwargs=dict(
            model=model_type,
            role_description=role_description_dict[ai_user_role]),
        task_specify_agent_kwargs=dict(model=model_type),
    )

    assert role_play_session is not None, (
        "RolePlaying instance should not be None")
    assert role_play_session.assistant_sys_msg.role_name is not None, (
        "RolePlaying instance should have assistant name")
    assert role_play_session.user_sys_msg.role_name is not None, (
        "RolePlaying instance should have user name")
    assert role_play_session.assistant_sys_msg.meta_dict[
        'assistant_description'] is not None, (
            "RolePlaying instance should have assistant description")
    assert role_play_session.user_sys_msg.meta_dict[
        'user_description'] is not None, (
            "RolePlaying instance should have user description")
