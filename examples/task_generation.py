import multiprocessing
import os

from camel.agent import ChatAgent
from camel.generator import (RoleNameGenerator, SystemMessageGenerator,
                             TaskPromptGenerator)
from camel.typing import ModeType, RoleType


def generate_tasks(role_name: str, task_generator_prompt: str,
                   start_token: str = "1.", num_tasks: int = 40) -> None:
    sys_msg_generator = SystemMessageGenerator()

    assistant_sys_msg = sys_msg_generator.from_role(RoleType.DEFAULT)
    assistant_agent = ChatAgent(assistant_sys_msg, ModeType.GPT_3_5_TURBO)

    assistant_sys_msg.content = task_generator_prompt
    user_msgs, _, _ = assistant_agent.step(assistant_sys_msg)
    user_msg = user_msgs[0]

    tasks = user_msg.content.split("\n")

    # Filter out the generated response to include the tasks only
    for i, task in enumerate(tasks):
        if start_token in task:
            tasks = tasks[i:i + num_tasks]
            break

    # Ensure exact number of tasks is generated
    assert str(num_tasks) in tasks[-1], print(tasks)

    with open(f"./tasks/{'_'.join(role_name)}.txt", "w") as file:
        file.write("\n".join(tasks))


def main() -> None:
    role_names_generator = RoleNameGenerator().from_role_files()
    task_generator_prompt_generator = TaskPromptGenerator().from_role_files()

    pool = multiprocessing.Pool(processes=1)
    for task_generator_prompt, role_name in zip(
            task_generator_prompt_generator, role_names_generator):
        if not os.path.exists(f"./tasks/{'_'.join(role_name)}.txt"):
            print(f"Generating tasks for {role_name}")
            pool.apply_async(generate_tasks,
                             (role_name, task_generator_prompt))

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
