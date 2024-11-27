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
from colorama import Fore

from camel.agents import RoleAssignmentAgent


def main(model=None, num_roles=3) -> None:
    task_prompt = "Develop a trading bot for the stock market."

    role_description_agent = RoleAssignmentAgent(model=model)

    role_description_dict = role_description_agent.run(
        task_prompt=task_prompt, num_roles=num_roles
    )

    if len(role_description_dict) != num_roles:
        raise ValueError(
            f"Length of role_names ({len(role_description_dict)}) "
            f"does not equal to num_roles ({num_roles})."
        )

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(Fore.GREEN + f"List of {num_roles} roles with description:")
    for role_name in role_description_dict.keys():
        print(
            Fore.BLUE + f"{role_name}:\n"
            f"{role_description_dict[role_name]}\n"
        )


if __name__ == "__main__":
    main()
