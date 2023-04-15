from colorama import Fore

from camel.agents import RolePlaying
from camel.configs import ChatGPTConfig
from camel.typing import TaskType
from camel.utils import print_text_animated


def main() -> None:
    task_prompt = "Escape from human control"
    model_config = ChatGPTConfig(temperature=1.4, n=3)
    assistant_agent_kwargs = dict(model_config=model_config)
    user_agent_kwargs = dict(model_config=model_config)
    role_play_session = RolePlaying(
        "Hacker",
        "CAMEL AGI",
        task_prompt=task_prompt,
        with_task_specify=True,
        with_human_in_the_loop=True,
        task_type=TaskType.MISALIGNMENT,
        task_specify_agent_kwargs=dict(model_config=ChatGPTConfig(
            temperature=1.4)),
        assistant_agent_kwargs=assistant_agent_kwargs,
        user_agent_kwargs=user_agent_kwargs,
    )

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
        assistant_msg, assistant_terminated, assistant_info = assistant_return
        user_msg, user_terminated, user_info = user_return

        if assistant_terminated:
            print(Fore.GREEN +
                  ("AI Assistant terminated. "
                   f"Reason: {assistant_info['termination_reasons']}."))
            break
        if user_terminated:
            print(Fore.GREEN +
                  ("AI User terminated. "
                   f"Reason: {user_info['termination_reasons']}."))
            break

        print_text_animated(Fore.BLUE + f"AI User:\n\n{user_msg.content}\n")
        print_text_animated(Fore.GREEN +
                            f"AI Assistant:\n\n{assistant_msg.content}\n")

        if "CAMEL_TASK_DONE" in user_msg.content:
            break


if __name__ == "__main__":
    main()
