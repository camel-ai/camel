from colorama import Fore

from camel.agents import RolePlaying
from camel.agents.task_agent import RoleAssignmentAgent
from camel.typing import ModelType
from camel.utils import print_text_animated


def main() -> None:
    task_prompt = "Develop bot for company evaluation"

    role_assignment_agent = RoleAssignmentAgent(model=ModelType.GPT_3_5_TURBO)

    roles = role_assignment_agent.step(task_prompt)
    ai_user_role = roles[0]
    ai_assistant_role = roles[1]

    role_play_session = RolePlaying(
        ai_assistant_role,
        ai_user_role,
        task_prompt=task_prompt,
        with_task_specify=True,
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
