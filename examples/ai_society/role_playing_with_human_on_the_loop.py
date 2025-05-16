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
import sys

from colorama import Fore

from camel.societies import RolePlaying
from camel.utils import get_human_intervention_manager


def main(model=None, chat_turn_limit=50) -> None:
    task_prompt = "Develop a trading bot for the stock market"
    role_play_session = RolePlaying(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=dict(model=model),
        with_human_on_the_loop=True,
        human_role_name="Human Trader",
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

    # Get the human intervention manager instance
    human_manager = get_human_intervention_manager()
    keyboard_mode = human_manager.start_keyboard_listener()

    try:
        n = 0
        input_msg = role_play_session.init_chat()

        while n < chat_turn_limit:
            n += 1
            human_manager.clear_keyboard_queue()

            assistant_response, user_response = role_play_session.step(
                input_msg
            )

            if assistant_response.terminated or user_response.terminated:
                print(Fore.GREEN + "Conversation terminated.")
                break

            human_manager.print_text_animated_interruptible(
                Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
            )
            human_manager.print_text_animated_interruptible(
                Fore.GREEN
                + f"AI Assistant:\n\n{assistant_response.msg.content}\n"
            )

            if human_manager.human_interrupt_requested.is_set():
                human_manager.human_intervention_handler(role_play_session)
                human_manager.human_interrupt_requested.clear()

            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break

            input_msg = assistant_response.msg

            if keyboard_mode:
                print(
                    Fore.MAGENTA
                    + "Continuing conversation... (press 'h' to intervene "
                    + "at any time)",
                    end="\r",
                )
                sys.stdout.flush()

    finally:
        if keyboard_mode:
            human_manager.stop_keyboard_listener()


if __name__ == "__main__":
    main()
