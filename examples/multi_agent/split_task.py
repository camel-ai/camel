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
import json

from colorama import Fore

from camel.agents.multi_agent import MultiAgent
from camel.configs import ChatGPTConfig


def main(model_type=None) -> None:
    task_prompt = "Develop a trading bot for the stock market."

    model_config_description = ChatGPTConfig()
    role_description_agent = MultiAgent(model_type=model_type,
                                        model_config=model_config_description)

    role_descriptions_dict = (role_description_agent.run_role_with_description(
        task_prompt=task_prompt, num_roles=4))

    num_subtasks = 6
    subtasks = role_description_agent.split_tasks(
        task_prompt=task_prompt, role_descriptions_dict=role_descriptions_dict,
        num_subtasks=num_subtasks)

    print(Fore.BLUE + f"Subtasks with description and dependencies:\n"
          f"{json.dumps(subtasks, indent=4)}")


if __name__ == "__main__":
    main()
