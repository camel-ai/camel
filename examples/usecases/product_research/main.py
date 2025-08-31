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

from typing import List

from colorama import Fore
from camel.configs import ChatGPTConfig
from camel.agents.chat_agent import ToolCallingRecord
from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.toolkits import (
    BrowserToolkit,
    AsyncBrowserToolkit,
    FileWriteToolkit,
    TerminalToolkit,
    PyAutoGUIToolkit,

)
import os

from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated
from camel.logger import get_logger, set_log_file,set_log_level
logger = get_logger(__name__)
# Set logging
set_log_file("product.log")
logger = get_logger(__name__)
set_log_level(level="DEBUG")
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.join(
    os.path.dirname(os.path.dirname(base_dir)), "workspace"
)


models = {
        "user": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1,
            model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
        ),
        "assistant": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1,
            model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
        ),
        "browsing": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1,
            model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
        ),
        "planning": ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1,
            model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
        ),


    }
async def main(
    chat_turn_limit=50,
) -> None:
    task_prompt = (
        
        "please give me a product research report for OWL:https://github.com/camel-ai/owl ."
        "let me know how to make it become an awesome commerical product."
        "then open the PDF by wps app in my local computer"
        "and then make a screenshot of this pdf"
    )



    tools_list = [
    
        *AsyncBrowserToolkit(
            headless=False,  # Set to True for headless mode (e.g., on remote servers)
            web_agent_model=models["browsing"],
            planning_agent_model=models["planning"],
        ).get_tools(),
        *PyAutoGUIToolkit().get_tools(),
        *TerminalToolkit(working_dir=workspace_dir).get_tools(),
        *FileWriteToolkit(output_dir="./").get_tools(),
    
     
    ]

    role_play_session = RolePlaying(
        assistant_role_name="product researcher",
        user_role_name="product manager",
        assistant_agent_kwargs=dict(
            model=models["assistant"],
            tools=tools_list,
        ),
        user_agent_kwargs=dict(
            model=models["user"],
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
    input_msg = await role_play_session.ainit_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = await role_play_session.astep(input_msg)

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
        for func_record in tool_calls:
            print_text_animated(f"{func_record}")
        print_text_animated(f"{assistant_response.msg.content}\n")

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
