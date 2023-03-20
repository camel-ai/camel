import json
import multiprocessing
import os

from camel_typing import (AssistantChatMessage, AssistantSystemMessage,
                          ModeType, RoleType, UserChatMessage,
                          UserSystemMessage)
from chat_agent import ChatAgent, TaskSpecifyAgent
from configs import ChatGPTConfig, SystemMessageGenerator


def init_chat(
    assistant_agent: ChatAgent,
    user_agent: ChatAgent,
    user_sys_msg: UserSystemMessage,
    assistant_sys_msg: AssistantSystemMessage,
):
    assistant_agent.reset()
    user_agent.reset()

    # Send the system messages again to the agents using chat messages
    assistant_msg = AssistantChatMessage(
        "Computer Programer",
        content=(f"{user_sys_msg.content}. "
                 "Now start to give me introductions one by one. "
                 "Only reply with Instruction and Input."))
    assistant_msg.role = "user"

    user_msg = UserChatMessage(user_sys_msg.role_name,
                               content=f"{assistant_sys_msg.content}")
    msgs, _, _ = assistant_agent.step(user_msg)

    return assistant_msg, msgs


def generate_data(assistant_idx: int, assistant_role_name: str, user_idx: int,
                  user_role_name: str, task_idx: int,
                  task_prompt: str) -> None:

    original_task_prompt = task_prompt
    task_specify_agent = TaskSpecifyAgent(ModeType.GPT_3_5_TURBO,
                                          ChatGPTConfig(temperature=1.4))
    specified_task_prompt = task_specify_agent.specify_task(
        original_task_prompt)

    sys_msg_generator = SystemMessageGenerator(with_task=True)
    assistant_sys_msg, user_sys_msg = sys_msg_generator.from_roles(
        roles=[(assistant_role_name, RoleType.ASSISTANT),
               (user_role_name, RoleType.USER)],
        task_prompt=specified_task_prompt)
    assistant_agent = ChatAgent(assistant_sys_msg, ModeType.GPT_3_5_TURBO)
    user_agent = ChatAgent(user_sys_msg, ModeType.GPT_3_5_TURBO)

    assistant_msg, _ = init_chat(assistant_agent, user_agent, user_sys_msg,
                                 assistant_sys_msg)

    message_counter = 1
    message_dict = {}

    # Append roles to the dictionary
    # We start number from 1 not 0.
    message_dict["role_1"] = f"{assistant_role_name}_{str(RoleType.ASSISTANT)}"
    message_dict["role_2"] = f"{user_role_name}_{str(RoleType.USER)}"
    message_dict[
        "id"] = f"{(assistant_idx+1):03}_{(user_idx+1):03}_{(task_idx+1):03}"
    message_dict["original_task"] = task_prompt.replace(f"{task_idx+1}. ", "")
    message_dict["specified_task"] = specified_task_prompt.replace(
        f"{task_idx+1}. ", "")

    # Threshold to terminate the conversation if no end token appears
    thank_counter = 0
    thank_threshold = 3

    while True:
        user_msgs, user_terminated, _ = user_agent.step(assistant_msg)
        if user_terminated:
            break
        user_msg = user_msgs[0]
        print(f"User:\n{user_msg.content}\n")
        user_msg.role = "user"

        if "<CAMEL_TASK_DONE>" in user_msg.content:
            break

        message_dict[f"message_{message_counter}"] = user_msg.to_dict()
        message_counter += 1

        assistant_msgs, assistant_terminated, _ = assistant_agent.step(
            user_msg)
        if assistant_terminated:
            break
        assistant_msg = assistant_msgs[0]
        print(f"Assistant:\n{assistant_msg.content}\n")
        assistant_msg.role = "user"

        message_dict[f"message_{message_counter}"] = assistant_msg.to_dict()
        message_counter += 1

        if "thank" in user_msg.content.lower():
            thank_counter += 1
            if thank_counter == thank_threshold:
                break
        else:
            thank_counter = 0

    message_dict["num_messages"] = message_counter

    with open(f"./camel_data/{message_dict['id']}.json", "w") as json_file:
        json.dump(message_dict, json_file)


def main() -> None:

    # Chunk for parallel jobs
    array_idx = int(os.environ.get('SLURM_ARRAY_TASK_ID'))
    roles_per_chunk = 10

    # Parameters for filtering the generated task string
    start_token = "1."
    num_tasks = 40

    with open("./data/user_roles.txt", "r") as f:
        user_roles = f.read().splitlines()

    with open("./data/assistant_roles.txt", "r") as f:
        assistant_roles = f.read().splitlines()

    assert (array_idx + 1) * roles_per_chunk <= len(assistant_roles)
    assistant_roles = assistant_roles[array_idx *
                                      roles_per_chunk:(array_idx + 1) *
                                      roles_per_chunk]

    pool = multiprocessing.Pool()

    for assistant_idx, assistant_role_name in enumerate(assistant_roles):
        for user_idx, user_role_name in enumerate(user_roles):

            # Load the task list assigned for assistant and user roles
            with open(f"./tasks/{assistant_role_name}_{user_role_name}.txt",
                      "r") as f:
                tasks = f.read().splitlines()

                # Filter out the generated response to include the tasks only
                for i, task in enumerate(tasks):
                    if start_token in task:
                        tasks = tasks[i:i + num_tasks]
                        break

                # Ensure exact number of tasks is generated
                assert str(num_tasks) in tasks[-1], print(tasks)

            for task_idx, task_prompt in enumerate(tasks):
                id = (f"{(assistant_idx+1):03}_"
                      f"{(user_idx+1):03}_{(task_idx+1):03}")
                if not os.path.exists(f"./camel_data/{id}.json"):
                    pool.apply_async(
                        generate_data,
                        (assistant_idx, assistant_role_name, user_idx,
                         user_role_name, task_idx, task_prompt))

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
