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

from camel.societies.role_play_adv import RolePlaying
from camel.utils import print_text_animated
from camel.typing import TaskType
import json


def main(model_type=None) -> None:
    task_prompt = "Play a game with another player, and win the highest score."
    role_play_session = RolePlaying(
        "Player 2",
        "Player 1",
        task_prompt=task_prompt,
        model_type=model_type,
        task_type=TaskType.GAME,
    )

    print(
        Fore.GREEN
        + f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n"
    )
    print(Fore.BLUE + f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

    print(f"{Fore.YELLOW}Original task prompt:\n{task_prompt}\n")

    chat_turn_limit, n = 120, 0
    user_msg, assistant_msg = role_play_session.init_chat()
    user_responses, assistant_responses = [], []
    while n < chat_turn_limit:
        n += 1
        assistant_response, user_response = role_play_session.step(
            user_msg, assistant_msg
        )
        user_responses.append(user_response)
        assistant_responses.append(assistant_response)
        user_msg = role_play_session.generate_next_round_msg(
            n, user_response, assistant_response, "Player 1"
        )
        assistant_msg = role_play_session.generate_next_round_msg(
            n, assistant_response, user_response, "Player 2"
        )
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

        print_text_animated(Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n")
        print_text_animated(
            f"{Fore.GREEN}AI Assistant:\n\n{assistant_response.msg.content}\n"
        )
        if "CAMEL_TASK_DONE" in user_response.msg.content:
            break

    chat_log = {
        "assistant_sys_msg": role_play_session.assistant_sys_msg.content,
        "user_sys_msg": role_play_session.user_sys_msg.content,
        "task_prompt": task_prompt,
        "chat_turn_limit": chat_turn_limit,
        "dialogue": [
            {
                "user": user_response.msg.content,
                "assistant": assistant_response.msg.content,
            }
            for user_response, assistant_response in zip(
                user_responses, assistant_responses
            )
        ],
        "option_res": role_play_session.option_res,
    }
    with open("chat_log.json", "w") as file:
        json.dump(chat_log, file)


if __name__ == "__main__":
    main()
