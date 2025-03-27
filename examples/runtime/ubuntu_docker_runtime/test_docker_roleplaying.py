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

from colorama import Fore

from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType
from camel.utils import print_text_animated

# Initialize terminal tools
tools = [*TerminalToolkit().get_tools()]

# Initialize the Qwen model with ModelScope API
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="Qwen/Qwen2.5-72B-Instruct",
    url='https://api-inference.modelscope.cn/v1/',
    # Replace with your ModelScope API key
    api_key="YOUR_MODELSCOPE_API_KEY_HERE",
)


def main(model=model, chat_turn_limit=50) -> None:
    r"""
    Main function to run the role-playing scenario.

    Args:
        model: The AI model instance to use for the conversation
        chat_turn_limit (int): Maximum number of conversation turns
                              (default: 50)

    Returns:
        None
    """
    # Define the task for the role-playing session
    task_prompt = "Develop a trading bot for the stock market"

    # Initialize the role-playing session
    role_play_session = RolePlaying(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=dict(model=model),
        output_language='en',  # Set output language to English
    )

    # Display initial system messages and prompts
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

    # Start the conversation loop
    n = 0
    input_msg = role_play_session.init_chat()
    while n < chat_turn_limit:
        print(input_msg)
        n += 1
        assistant_response, user_response = role_play_session.step(input_msg)

        # Display current system environment for debugging
        print(os.environ)

        # Check for conversation termination
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

        # Display conversation messages
        print_text_animated(
            Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
        )
        print_text_animated(
            Fore.GREEN + "AI Assistant:\n\n"
            f"{assistant_response.msg.content}\n"
        )

        # Check if task is completed
        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg


if __name__ == "__main__":
    main()
