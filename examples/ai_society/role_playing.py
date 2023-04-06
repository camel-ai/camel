import time

from colorama import Fore

from camel.agent import RolePlaying


def print_text_animated(text):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(0.02)


def main() -> None:
    task_prompt = "Develop a trading bot for the stock market"
    role_play_session = RolePlaying("Python Programmer", "Stock Trader",
                                    task_prompt, with_task_specify=True,
                                    with_task_planner=False)

    print(
        Fore.GREEN +
        f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n")
    print(Fore.BLUE +
          f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN +
        f"Specified task prompt:\n{role_play_session.specified_task_prompt}\n")
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    chat_turn_limit, n = 50, 0
    assistant_msg, _ = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_return, user_return = role_play_session.step(assistant_msg)
        assistant_msg, _, _ = assistant_return
        user_msg, _, _ = user_return
        print_text_animated(Fore.BLUE + f"AI User:\n\n{user_msg.content}\n\n")
        time.sleep(0.5)
        print_text_animated(Fore.GREEN +
                            f"AI Assistant:\n\n{assistant_msg.content}\n\n")

        if "CAMEL_TASK_DONE" in user_msg.content:
            break


if __name__ == "__main__":
    main()
