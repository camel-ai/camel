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

from getpass import getpass

from camel.societies.workforce.dynamic_agent import DynamicAgentCreator
from camel.societies.workforce.tool_selector import ACIFunctionToolSelector


def main():
    linked_account_owner_id = getpass(
        "Enter your ACI linked account owner ID: "
    )

    tool_selector = ACIFunctionToolSelector(
        linked_account_owner_id=linked_account_owner_id
    )

    agent_creator = DynamicAgentCreator(tool_selector=tool_selector)

    task_content = "Search for GitHub repositories related to 'AI agents'"

    agent = agent_creator.create_agent(task_content)

    print(f"\nStarting task: {task_content}")
    response = agent.step(task_content)

    if response and response.msgs:
        print("\nAgent Response:")
        print(response.msgs[0].content)
    else:
        print("No response received from the agent.")


if __name__ == "__main__":
    main()
