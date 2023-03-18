import multiprocessing
import os

from camel_typing import ModeType, RoleType
from chat_agent import ChatAgent
from configs import (RoleNameGenerator, SystemMessageGenerator,
                     TaskPromptGenerator)


def process_task(role_name: str, task_prompt: str) -> None:
    sys_msg_generator = SystemMessageGenerator()

    assistant_sys_msg = sys_msg_generator.from_role(RoleType.DEFAULT)
    assistant_agent = ChatAgent(assistant_sys_msg, ModeType.GPT_3_5_TURBO)

    assistant_sys_msg.content = task_prompt
    user_msgs, _, _ = assistant_agent.step(assistant_sys_msg)
    user_msg = user_msgs[0]

    with open(f"./tasks/{'_'.join(role_name)}.txt", "w") as file:
        file.write(user_msg.content)


def main() -> None:
    role_names_generator = RoleNameGenerator().from_role_files()
    task_prompt_generator = TaskPromptGenerator().from_role_generator(
        role_names_generator)

    pool = multiprocessing.Pool()
    for task_prompt, role_name in zip(task_prompt_generator,
                                      role_names_generator):
        if not os.path.exists(f"./tasks/{'_'.join(role_name)}.txt"):
            pool.apply_async(process_task, (role_name, task_prompt))

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
