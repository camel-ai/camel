from camel.agent import RolePlaying


def main() -> None:
    task_prompt = "Developing custom game mods or plugins"
    print(f"Original task prompt:\n{task_prompt}\n")
    role_play_session = RolePlaying("Computer Programer", "Gamer", task_prompt)
    print(f"Specified task prompt:\n{role_play_session.task_prompt}\n")

    chat_turn_limit, n = 10, 0
    assistant_msg, _ = role_play_session.init_chat()
    while n < chat_turn_limit:
        n += 1
        assistant_msg, user_msg = role_play_session.step(assistant_msg)
        print(f"AI User:\n\n{user_msg.content}\n\n")
        print(f"AI Assistant:\n\n{assistant_msg.content}\n\n")


if __name__ == "__main__":
    main()
