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

from typing import Dict, List, Optional, Tuple

from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.types import ModelPlatformType
from camel.utils import print_text_animated

"""
Please set the below environment variable before running this example:
export VOLCANO_API_KEY="your_volcano_api_key"

This example demonstrates how to use Volcano Engine API with DeepSeek models
for role-playing in CAMEL.
"""


def main(
    assistant_role_name: str = "Python Programmer",
    user_role_name: str = "Stock Market Trader",
    task_prompt: str = (
        "Develop a Python script that analyzes historical stock data "
        "and identifies potential buying opportunities based on "
        "technical indicators."
    ),
    with_task_specify: bool = True,
    model_config_dict: Optional[Dict] = None,
) -> Tuple[List[Dict], List[Dict]]:
    r"""Run a role-playing session with Volcano Engine API.

    Args:
        assistant_role_name: The role name of the assistant.
        user_role_name: The role name of the user.
        task_prompt: The task prompt.
        with_task_specify: Whether to specify the task.
        model_config_dict: The model configuration dictionary.

    Returns:
        A tuple of assistant and user message lists.
    """
    if model_config_dict is None:
        model_config_dict = {
            "temperature": 0.2,
            "max_tokens": 1024,
        }

    # Create models for assistant and user
    assistant_model = ModelFactory.create(
        model_platform=ModelPlatformType.VOLCANO,
        model_type="deepseek-r1-250120",
        model_config_dict=model_config_dict,
    )

    user_model = ModelFactory.create(
        model_platform=ModelPlatformType.VOLCANO,
        model_type="deepseek-r1-250120",
        model_config_dict=model_config_dict,
    )

    # Create a role-playing session
    role_playing = RolePlaying(
        assistant_role_name=assistant_role_name,
        user_role_name=user_role_name,
        assistant_agent_kwargs={"model": assistant_model},
        user_agent_kwargs={"model": user_model},
        task_prompt=task_prompt,
        with_task_specify=with_task_specify,
    )

    # Start the role-playing session
    print(
        f"Running role-playing with Volcano Engine API (DeepSeek-R1)...\n"
        f"Assistant Role: {assistant_role_name}\n"
        f"User Role: {user_role_name}\n"
        f"Task: {task_prompt}\n"
    )

    # Start the chat
    chat_history = []
    n = 0
    input_msg = role_playing.init_chat()  # Initialize the chat
    while n < 10:
        n += 1
        assistant_response, user_response = role_playing.step(
            input_msg
        )  # Provide input_msg
        if assistant_response is None or user_response is None:
            break

        chat_history.append(
            {
                "role": "assistant",
                "content": assistant_response.msg.content,
            }
        )
        chat_history.append(
            {"role": "user", "content": user_response.msg.content}
        )

        print_text_animated(f"Assistant ({assistant_role_name}):\n")
        print_text_animated(f"{assistant_response.msg.content}\n")
        print_text_animated(f"User ({user_role_name}):\n")
        print_text_animated(f"{user_response.msg.content}\n")

        if "<CAMEL_TASK_DONE>" in user_response.msg.content:
            break

        input_msg = (
            assistant_response.msg
        )  # Update input_msg for the next step

    # return role_playing.assistant_agent.chat_history, role_playing.
    # user_agent.chat_history


if __name__ == "__main__":
    main()
