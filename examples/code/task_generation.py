import multiprocessing
import os

from camel.agent import ChatAgent
from camel.generator import CodeTaskPromptGenerator, SystemMessageGenerator
from camel.typing import ModeType, RoleType, TaskType


def generate_tasks(task_generator_prompt: str, language: str, domain: str,
                   start_token: str = "1.", num_tasks: int = 10) -> None:
    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.DEFAULT)
    assistant_sys_msg = sys_msg_generator.from_dict(
        dict(), role_tuple=("Task Generator", RoleType.DEFAULT))
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

    with open(f"./code/tasks/{language}_{domain}.txt", "w") as file:
        file.write("\n".join(tasks))


def main() -> None:
    num_tasks = 50
    start_token = "1."

    task_generator_prompt_gen = CodeTaskPromptGenerator(
        num_tasks=num_tasks).from_role_files()

    pool = multiprocessing.Pool()
    for task_generator_prompt, language, domain in task_generator_prompt_gen:
        if not os.path.exists(f"./code/tasks/{language}_{domain}.txt"):
            print(language, domain)

            pool.apply_async(generate_tasks, (task_generator_prompt, language,
                                              domain, start_token, num_tasks))

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
