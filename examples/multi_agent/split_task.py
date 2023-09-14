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

from camel.agents.role_assignment_agent import RoleAssignmentAgent
from camel.configs import ChatGPTConfig


def main(model_type=None) -> None:
    task_prompt = "Develop a trading bot for the stock market."

    model_config_description = ChatGPTConfig()
    role_assignment_agent = RoleAssignmentAgent(
        model=model_type, model_config=model_config_description)

    role_description_dict = role_assignment_agent.run(task_prompt=task_prompt,
                                                      num_roles=4)

    num_subtasks = 6

    subtasks = role_assignment_agent.split_tasks(task_prompt,
                                                 role_description_dict,
                                                 num_subtasks)

    if subtasks is None:
        raise ValueError("subtasks is None.")
    if len(subtasks) != num_subtasks:
        raise ValueError(f"Number of subtasks ({len(subtasks)}) "
                         f"does not equal to num_subtasks ({num_subtasks}).")

    for (i, subtask) in enumerate(subtasks):
        print(Fore.BLUE + f"Subtask {i + 1}. {subtask}")
    for (i, (role_name,
             role_description)) in enumerate(role_description_dict.items()):
        print(Fore.GREEN + f"Role {i + 1}. {role_name}: {role_description}")


if __name__ == "__main__":
    main()
