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

from camel.societies import BabyAGI
from camel.utils import print_text_animated


def main(model=None, chat_turn_limit=15) -> None:
    task_prompt = "Develop a trading bot for the stock market"
    babyagi_session = BabyAGI(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        task_prompt=task_prompt,
        task_specify_agent_kwargs=dict(model=model),
    )

    print(
        Fore.GREEN
        + f"AI Assistant sys message:\n{babyagi_session.assistant_sys_msg}\n"
    )

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN
        + f"Specified task prompt:\n{babyagi_session.specified_task_prompt}\n"
    )
    print(
        Fore.RED
        + f"Final task prompt:\n{babyagi_session.specified_task_prompt}\n"
    )

    n = 0
    while n < chat_turn_limit:
        n += 1
        assistant_response = babyagi_session.step()
        if assistant_response.terminated:
            print(
                Fore.GREEN
                + (
                    "AI Assistant terminated. Reason: "
                    f"{assistant_response.info['termination_reasons']}."
                )
            )
            break
        print_text_animated(
            Fore.RED + "Task Name:\n\n"
            f"{assistant_response.info['task_name']}\n"
        )
        print_text_animated(
            Fore.GREEN + "AI Assistant:\n\n"
            f"{assistant_response.msg.content}\n"
        )
        print_text_animated(
            Fore.BLUE + "Remaining Subtasks:\n\n"
            f"{assistant_response.info['subtasks'][:5]}\n"
        )


if __name__ == "__main__":
    main()
