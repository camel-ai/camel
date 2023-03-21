import time

from camel.agent import RolePlaying


def print_text_animated(text):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(0.02)


def main() -> None:
    task_prompt = "Design a custom game using PyGame"
    print(f"Original task prompt:\n{task_prompt}\n")
    role_play_session = RolePlaying("Computer Programer", "Gamer", task_prompt)
    print(f"Specified task prompt:\n{role_play_session.task_prompt}\n")

    chat_turn_limit, n = 10, 0
    assistant_msg, _ = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_msg, user_msg = role_play_session.step(assistant_msg)
        print_text_animated(f"AI User:\n\n{user_msg.content}\n\n")
        time.sleep(2.5)
        print_text_animated(f"AI Assistant:\n\n{assistant_msg.content}\n\n")

        if "<CAMEL_TASK_DONE>" in assistant_msg.content:
            break


if __name__ == "__main__":
    main()
