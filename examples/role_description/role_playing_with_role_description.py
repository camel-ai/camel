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
from colorama import Fore

from camel.agents.role_assignment import RoleAssignmentAgent
from camel.configs import ChatGPTConfig
from camel.societies import RolePlaying
from camel.typing import TaskType
from camel.utils import print_text_animated

AI_ASSISTANT_ROLE_INDEX = 0
AI_USER_ROLE_INDEX = 1


def main(model_type=None) -> None:
    task_prompt = "Develop a trading bot for the stock market."

    model_config_description = ChatGPTConfig()
    role_description_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)

    role_names, role_description_dict, _, _ = (
        role_description_agent.run_role_with_description(
            task_prompt=task_prompt, num_roles=2))

    ai_assistant_role = role_names[AI_ASSISTANT_ROLE_INDEX]
    ai_user_role = role_names[AI_USER_ROLE_INDEX]

    role_play_session = RolePlaying(
        task_prompt=task_prompt,
        task_type=TaskType.ROLE_DESCRIPTION,  # important for role description
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

    print(
        Fore.GREEN +
        f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n")
    print(Fore.BLUE +
          f"AI User sys message:\n{role_play_session.user_sys_msg}\n")
    print(Fore.GREEN + f"AI Assistant role description:\n"
          f"{role_play_session.assistant_sys_msg.role_name}\n"
          f"{role_description_dict[ai_assistant_role]}\n")
    print(Fore.BLUE + f"AI User role description:\n"
          f"{role_play_session.user_sys_msg.role_name}\n"
          f"{role_description_dict[ai_user_role]}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN +
        f"Specified task prompt:\n{role_play_session.specified_task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    chat_turn_limit, n = 50, 0
    input_assistant_msg, _ = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(
            input_assistant_msg)

        if assistant_response.terminated:
            print(Fore.GREEN + (
                "AI Assistant terminated. "
                f"Reason: {assistant_response.info['termination_reasons']}."))
            break
        if user_response.terminated:
            print(Fore.GREEN +
                  ("AI User terminated. "
                   f"Reason: {user_response.info['termination_reasons']}."))
            break

        print_text_animated(
            Fore.BLUE +
            f"AI User: {ai_user_role}\n\n{user_response.msg.content}\n")
        print_text_animated(Fore.GREEN +
                            f"AI Assistant:{ai_assistant_role}\n\n" +
                            f"{assistant_response.msg.content}\n")

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_assistant_msg = assistant_response.msg


if __name__ == "__main__":
    main()
