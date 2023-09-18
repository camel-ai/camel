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

    # Run task assignment to generate dependencies among subtasks
    dag_json = role_assignment_agent.run_task_assignment(task_prompt, subtasks)

    if not dag_json:
        raise ValueError("Dependency graph (DAG) is empty.")

    print(Fore.BLUE + "\nDependencies among subtasks: ")
    print(json.dumps(dag_json, indent=4))
    for (i, subtask) in enumerate(subtasks):
        print(Fore.GREEN + f"\nSubtasks {i+1}: {subtask}")
        subtask_key = f"Subtask{i+1}"
        dependencies = dag_json.get(subtask_key, {}).get("dependencies", [])
        if dependencies:
            print(Fore.CYAN + "Dependencies: ", ", ".join(dependencies))
        else:
            print(Fore.RED + "No Dependencies Found.")


if __name__ == "__main__":
    main()
