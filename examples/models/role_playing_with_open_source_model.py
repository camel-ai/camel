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

from camel.configs import ChatGPTConfig, OpenSourceConfig
from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated


# Here :obj:`model_type` can be any of the supported open-source
# model types and :obj:`model_path` should be set corresponding to
# model type. For example, to use Vicuna, we can set:
# model_path = "lmsys/vicuna-7b-v1.5"
def main(
    chat_turn_limit=50,
    model_platform=ModelPlatformType.OPEN_SOURCE,
    model_type=ModelType.STUB,
    model_path="meta-llama/Llama-2-7b-chat-hf",
    server_url="http://localhost:8000/v1",
) -> None:
    task_prompt = "Develop a trading bot for the stock market"

    model = ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
        model_config_dict=OpenSourceConfig(
            model_path=model_path,
            server_url=server_url,
            api_params=ChatGPTConfig(temperature=0),
        ).as_dict(),
    )

    # Update agent_kwargs to use the created models
    agent_kwargs = {
        "assistant": {"model": model},
        "user": {"model": model},
        "task-specify": {"model": model},
    }

    role_play_session = RolePlaying(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=agent_kwargs["assistant"],
        user_role_name="Stock Trader",
        user_agent_kwargs=agent_kwargs["user"],
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=agent_kwargs["task-specify"],
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

        print_text_animated(
            Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
        )
        print_text_animated(
            Fore.GREEN + "AI Assistant:\n\n"
            f"{assistant_response.msg.content}\n"
        )

        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

        input_msg = assistant_response.msg


if __name__ == "__main__":
    main()
