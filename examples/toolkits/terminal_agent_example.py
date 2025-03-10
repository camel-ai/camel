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

import os
from typing import List

from colorama import Fore

from camel.agents.chat_agent import ToolCallingRecord
from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated


def main(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    chat_turn_limit=10,
) -> None:
    # Get the current script directory as base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    task_prompt = (
        "Complete the following log management tasks:\n\n"
        "1. Create a log directory:\n"
        f"   - Create a 'logs' directory in '{base_dir}'\n\n"
        "2. Create and write log files:\n"
        "   - Create 'app.log' with content: 'INFO: Application started successfully at 2024-03-10'\n"
        "   - Create 'error.log' with content: 'ERROR: Database connection timeout at 2024-03-10'\n\n"
        "3. Search logs:\n"
        "   - Search for 'ERROR' keyword in 'error.log'\n\n"
        "4. List files:\n"
        "   - Find all .log files in the 'logs' directory\n\n"
        "5. Append new log entries:\n"
        "   - Append to 'app.log': 'INFO: Processing user request #1234'\n"
        "   - Append to 'error.log': 'ERROR: Invalid user input for request #1234'\n\n"
        "6. Search logs again:\n"
        "   - Search for lines containing '#1234' in both log files\n\n"
        "7. Clean up:\n"
        "   - Remove the 'logs' directory and all its contents\n\n"
        "Important Notes:\n"
        "1. You have access to TerminalToolkit tools that can help you execute shell commands and search files\n"
        "2. Think about which shell commands would be appropriate for each task\n"
        "3. Remember to use absolute paths and handle errors appropriately\n"
        "4. Verify the results after each operation"
    )

    tools_list = TerminalToolkit().get_tools()

    role_play_session = RolePlaying(
        assistant_role_name="System Administrator",
        user_role_name="DevOps Manager",
        assistant_agent_kwargs=dict(
            model=ModelFactory.create(
                model_platform=model_platform,
                model_type=model_type,
            ),
            tools=tools_list,
        ),
        user_agent_kwargs=dict(
            model=ModelFactory.create(
                model_platform=model_platform,
                model_type=model_type,
            ),
        ),
        task_prompt=task_prompt,
        with_task_specify=False,
    )

    print(
        Fore.GREEN
        + f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n"
    )
    print(
        Fore.BLUE + f"AI User sys message:\n{role_play_session.user_sys_msg}\n"
    )

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN
        + "Specified task prompt:"
        + f"\n{role_play_session.specified_task_prompt}\n"
    )
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    n = 0
    input_msg = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(input_msg)

        if assistant_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI Assistant terminated. Reason: "
                    f"{assistant_response.info['termination_reasons']}."
                )
            )
            break
        if user_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI User terminated. "
                    f"Reason: {user_response.info['termination_reasons']}."
                )
            )
            break

        # Print output from the user
        print_text_animated(
            Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
        )

        # Print output from the assistant, including any function
        # execution information
        print_text_animated(Fore.GREEN + "AI Assistant:")
        tool_calls: List[ToolCallingRecord] = [
            ToolCallingRecord(**call.as_dict())
            for call in assistant_response.info['tool_calls']
        ]
        
        # Track tool usage
        if tool_calls:
            print_text_animated(Fore.YELLOW + "\nTool Usage:")
            for func_record in tool_calls:
                print_text_animated(f"\nTool Call Record: {func_record}")
        else:
            print_text_animated(
                Fore.RED + "\nWarning: No tools were used in this response!")
            
        print_text_animated(f"\n{assistant_response.msg.content}\n")

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg


if __name__ == "__main__":
    main()
