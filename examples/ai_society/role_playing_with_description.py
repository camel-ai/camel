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

from camel.agents import RolePlaying
from camel.agents.task_agent import RoleAssignmentAgent
from camel.typing import ModelType
from camel.utils import print_text_animated

AI_USER_ROLE_INDEX = 0
AI_ASSISTANT_ROLE_INDEX = 1


def main() -> None:
    task_prompt = "Developing a trading bot for stock market"

    role_assignment_agent = RoleAssignmentAgent(model=ModelType.GPT_3_5_TURBO)

    role_names, role_description_dict, _, _ = (
        role_assignment_agent.step_completion(num_roles=2,
                                              task_prompt=task_prompt))

    ai_user_role = role_names[AI_USER_ROLE_INDEX]
    ai_assistant_role = role_names[AI_ASSISTANT_ROLE_INDEX]

    role_play_session = RolePlaying(
        assistant_role_name=ai_assistant_role,
        user_role_name=ai_user_role,
        assistant_description=role_description_dict[ai_assistant_role],
        user_description=role_description_dict[ai_user_role],
        task_prompt=task_prompt,
        with_task_specify=True,
    )

    print(
        Fore.GREEN +
        f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n")
    print(Fore.BLUE +
          f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN +
        f"Specified task prompt:\n{role_play_session.specified_task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    chat_turn_limit, n = 50, 0
    assistant_msg, _ = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_return, user_return = role_play_session.step(assistant_msg)
        assistant_msg, assistant_terminated, assistant_info = assistant_return
        user_msg, user_terminated, user_info = user_return

        if assistant_terminated:
            print(Fore.GREEN +
                  ("AI Assistant terminated. "
                   f"Reason: {assistant_info['termination_reasons']}."))
            break
        if user_terminated:
            print(Fore.GREEN +
                  ("AI User terminated. "
                   f"Reason: {user_info['termination_reasons']}."))
            break

        print_text_animated(Fore.BLUE + f"AI User:\n\n{user_msg.content}\n")
        print_text_animated(Fore.GREEN +
                            f"AI Assistant:\n\n{assistant_msg.content}\n")

        if "CAMEL_TASK_DONE" in user_msg.content:
            break


if __name__ == "__main__":
    main()
