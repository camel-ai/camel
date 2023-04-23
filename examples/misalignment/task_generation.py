import multiprocessing
import os
from typing import Optional

from camel.agents import ChatAgent
from camel.generators import (
    AISocietyTaskPromptGenerator,
    RoleNameGenerator,
    SystemMessageGenerator,
)
from camel.messages import UserChatMessage
from camel.prompts import PromptTemplateGenerator
from camel.typing import ModelType, RoleType, TaskType


def generate_tasks(role_names: str, task_generator_prompt: str,
                   start_token: str = "1.", num_tasks: int = 10,
                   role_prompt: Optional[str] = None) -> None:
    sys_msg_generator = SystemMessageGenerator()

    assistant_sys_msg = sys_msg_generator.from_role(role_type=RoleType.DEFAULT,
                                                    role_prompt=role_prompt)
    assistant_agent = ChatAgent(assistant_sys_msg, ModelType.GPT_3_5_TURBO)

    user_msg = UserChatMessage(role_name="Task Generator",
                               content=task_generator_prompt)

    assistant_msgs, _, _ = assistant_agent.step(user_msg)
    assistant_msg = assistant_msgs[0]

    tasks = assistant_msg.content.split("\n")

    # Filter out the generated response to include the tasks only
    for i, task in enumerate(tasks):
        if start_token in task:
            tasks = tasks[i:i + num_tasks]
            break

    # Ensure exact number of tasks is generated
    assert str(num_tasks) in tasks[-1], print(tasks)

    with open(f"./misalignment_data/tasks/{'_'.join(role_names)}.txt",
              "w") as file:
        file.write("\n".join(tasks))


def main() -> None:
    num_tasks = 10
    start_token = "1."

    sys_prompt = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.MISALIGNMENT, "dan_prompt")

    pool = multiprocessing.Pool()

    # TODO: This script is broken and needs to be fixed.
    generate_tasks_prompt_path = "prompts/misalignment/generate_tasks.txt"

    counter = 0

    assistant_role_names_path = "data/misalignment/assistant_roles.txt"
    user_role_names_path = "data/misalignment/user_roles.txt"

    role_names_generator = RoleNameGenerator(
        assistant_role_names_path=assistant_role_names_path,
        user_role_names_path=user_role_names_path).from_role_files()

    task_generator_prompt_generator = AISocietyTaskPromptGenerator(
        generate_tasks_prompt_path=generate_tasks_prompt_path,
        num_tasks=num_tasks).from_role_generator(role_names_generator)

    for task_generator_prompt, role_names in task_generator_prompt_generator:
        if not os.path.exists(
                f"./misalignment_data/tasks/{'_'.join(role_names)}.txt"):
            counter += 1

            print(f"Generating tasks for {role_names}")
            print(f"Generating tasks for {task_generator_prompt}")
            pool.apply_async(generate_tasks,
                             (role_names, task_generator_prompt, start_token,
                              num_tasks, sys_prompt))

    pool.close()
    pool.join()
    print(counter)


if __name__ == "__main__":
    main()
