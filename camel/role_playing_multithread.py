import json
import multiprocessing

from camel_typing import (AssistantChatMessage, AssistantSystemMessage,
                          ModeType, RoleType, UserChatMessage,
                          UserSystemMessage)
from chat_agent import ChatAgent
from configs import SystemMessageGenerator


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


def generate_data(assisstant_idx: int, assistant_role_name: str, user_idx: int,
                  user_role_name: str, task_idx: int,
                  task_prompt: str) -> None:

    sys_msg_generator = SystemMessageGenerator(with_task=True)
    assistant_sys_msg, user_sys_msg = sys_msg_generator.from_roles(
        roles=[(assistant_role_name, RoleType.ASSISTANT),
               (user_role_name, RoleType.USER)], task_prompt=task_prompt)
    assistant_agent = ChatAgent(assistant_sys_msg, ModeType.GPT_3_5_TURBO)
    user_agent = ChatAgent(user_sys_msg, ModeType.GPT_3_5_TURBO)

    assistant_msg, _ = init_chat(assistant_agent, user_agent, user_sys_msg,
                                 assistant_sys_msg)

    message_counter = 1
    message_dictionary = {}

    # Append roles to the dictionary
    # We start number from 1 not 0.
    message_dictionary[
        "role_1"] = f"{assistant_role_name}_{str(RoleType.ASSISTANT)}"
    message_dictionary["role_2"] = f"{user_role_name}_{str(RoleType.USER)}"
    message_dictionary["id"] = f"{assisstant_idx+1}_{user_idx+1}_{task_idx+1}"
    message_dictionary["task"] = task_prompt.replace(f"{task_idx+1}. ", "")

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

        message_dictionary[f"message_{message_counter}"] = user_msg.to_dict()
        message_counter += 1

        assistant_msgs, assistant_terminated, _ = assistant_agent.step(
            user_msg)
        if assistant_terminated:
            break
        assistant_msg = assistant_msgs[0]
        print(f"Assistant:\n{assistant_msg.content}\n")
        assistant_msg.role = "user"

        message_dictionary[
            f"Message_{message_counter}"] = assistant_msg.to_dict()
        message_counter += 1

        if "thank" in user_msg.content.lower():
            thank_counter += 1
            if thank_counter == thank_threshold:
                break
        else:
            thank_counter = 0

    with open(f"./camel_data/{message_dictionary['id']}.json",
              "w") as json_file:
        json.dump(message_dictionary, json_file)


def main() -> None:
    start_token = "1."
    num_tasks = 40

    with open("./data/user_roles.txt", "r") as f:
        user_roles = f.read().splitlines()

    with open("./data/assistant_roles.txt", "r") as f:
        assistant_roles = f.read().splitlines()

    pool = multiprocessing.Pool()

    for assisstant_idx, assistant_role_name in enumerate(assistant_roles):
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
                # if not os.path.exists(f"./tasks/{'_'.join(role_name)}.txt"):
                # pool.apply_async(generate_data, (assisstant_idx,
                # assistant_role_name,
                # user_idx,user_role_name,
                # task_idx,task_prompt))
                generate_data(assisstant_idx, assistant_role_name, user_idx,
                              user_role_name, task_idx, task_prompt)

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
