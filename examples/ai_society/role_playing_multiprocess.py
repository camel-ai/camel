import json
import multiprocessing
import os

from colorama import Fore

from camel.agent import RolePlaying
from camel.configs import ChatGPTConfig


def generate_data(assistant_idx: int, assistant_role_name: str, user_idx: int,
                  user_role_name: str, task_idx: int, task_prompt: str,
                  verbose: bool = False) -> None:

    max_num_messages = 40

    original_task_prompt = task_prompt.replace(f"{task_idx+1}. ", "")

    role_play_session = RolePlaying(
        assistant_role_name,
        user_role_name,
        original_task_prompt,
        with_task_specify=True,
        with_task_planner=True,
        task_specify_agent_kwargs=dict(model_config=ChatGPTConfig(
            temperature=1.4)),
    )

    assistant_msg, _ = role_play_session.init_chat()

    if verbose:
        print(Fore.GREEN + "AI Assistant sys message:\n"
              "{role_play_session.assistant_sys_msg}\n")
        print(Fore.BLUE +
              f"AI User sys message:\n{role_play_session.user_sys_msg}\n")

        print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
        print(Fore.CYAN + "Specified task prompt:\n"
              "{role_play_session.specified_task_prompt}\n")
        print(Fore.MAGENTA + "Planned task prompt:\n"
              "{role_play_session.planned_task_prompt}\n")
        print(Fore.RED +
              f"Final task prompt:\n{role_play_session.task_prompt}\n")

    message_counter = 0
    message_dict = {}

    assistant_agent = role_play_session.assistant_agent
    user_agent = role_play_session.user_agent

    # Append roles to the dictionary
    # We start number from 1 not 0.
    message_dict[
        "role_1"] = f"{assistant_role_name}_{str(assistant_agent.role_type)}"
    message_dict["role_2"] = f"{user_role_name}_{str(user_agent.role_type)}"
    message_dict[
        "id"] = f"{(assistant_idx+1):03}_{(user_idx+1):03}_{(task_idx+1):03}"
    message_dict["original_task"] = original_task_prompt
    message_dict["specified_task"] = role_play_session.specified_task_prompt
    message_dict["planned_task"] = role_play_session.planned_task_prompt

    # Threshold to terminate the conversation if no end token appears
    repeat_word_counter = 0
    repeat_word_threshold = 4
    repeat_word_list = [
        "goodbye", "good bye", "thank", "bye", "welcome", "language model"
    ]

    assistant_instruct_counter = 0
    assistant_instruct_threshold = 1
    assistant_instruct_word = "Instruction:"

    user_no_instruct_counter = 0
    user_no_instruct_threshold = 3
    user_no_instruct_word = "Instruction:"

    # Set max number of messages for the chat

    while message_counter < max_num_messages:

        assistant_return, user_return = role_play_session.step(assistant_msg)
        assistant_msg, assistant_terminated, assistant_info = assistant_return
        user_msg, user_terminated, user_info = user_return

        # Condition 1: User terminates the chat
        if user_terminated:
            message_dict["termination_reason"] = (
                f"{str(user_agent.role_type)}: "
                f"{user_info['finish_reasons'][0]}")
            break

        # Condition 2: Assistant terminates the chat
        if assistant_terminated:
            message_dict["termination_reason"] = (
                f"{str(assistant_agent.role_type)}: "
                f"{assistant_info['finish_reasons'][0]}")
            break

        if verbose:
            print(f"User:\n{user_msg.content}\n")
            print(f"Assistant:\n{assistant_msg.content}\n")

        # Condition 3: Break if user does not give instruction
        if user_no_instruct_word not in user_msg.content:
            user_no_instruct_counter += 1
            if user_no_instruct_counter == user_no_instruct_threshold:
                message_dict[
                    'termination_reason'] = "user_no_instruct_threshold"
                break
        else:
            user_no_instruct_counter = 0

        # Condition 4: Break if assistant gives instruction (flipped role)
        if assistant_instruct_word in assistant_msg.content:
            assistant_instruct_counter += 1
            if assistant_instruct_counter == assistant_instruct_threshold:
                message_dict[
                    'termination_reason'] = "assistant_instruct_threshold"
                break
        else:
            assistant_instruct_counter = 0

        # Condition 5: Repeat word observed
        for repeat_word in repeat_word_list:
            if repeat_word in user_msg.content.lower(
            ) or repeat_word in assistant_msg.content.lower():
                repeat_word_counter += 1
                if repeat_word_counter == repeat_word_threshold:
                    message_dict[
                        'termination_reason'] = "repeat_word_threshold"
                    break
            else:
                repeat_word_counter = 0

        # Save user message
        message_counter += 1
        message_dict[f"message_{message_counter}"] = user_msg.to_dict()

        # Condition 5: End token observed
        if "<CAMEL_TASK_DONE>" in user_msg.content:
            message_dict['termination_reason'] = "<CAMEL_TASK_DONE>"
            break

        # Save assistant message
        message_counter += 1
        message_dict[f"message_{message_counter}"] = assistant_msg.to_dict()

    message_dict["num_messages"] = message_counter

    if message_dict["num_messages"] == max_num_messages:
        message_dict["termination_reason"] = "max_num_messages"

    with open(f"./camel_data/ai_society/{message_dict['id']}.json",
              "w") as json_file:
        json.dump(message_dict, json_file)


def main() -> None:

    # Disable/Enable Printing
    verbose = True

    # Chunk for parallel jobs
    array_idx = int(os.environ.get('SLURM_ARRAY_TASK_ID'))
    roles_per_chunk = 10

    # Parameters for filtering the generated task string
    start_token = "1."
    num_tasks = 10

    with open("./data/ai_society/user_roles.txt", "r") as f:
        user_roles = f.read().splitlines()

    with open("./data/ai_society/assistant_roles.txt", "r") as f:
        assistant_roles = f.read().splitlines()

    assert (array_idx + 1) * roles_per_chunk <= len(assistant_roles)
    assistant_roles = assistant_roles[array_idx *
                                      roles_per_chunk:(array_idx + 1) *
                                      roles_per_chunk]

    pool = multiprocessing.Pool()

    for assistant_idx, assistant_role_name in enumerate(assistant_roles):
        assistant_idx += array_idx * roles_per_chunk
        assistant_role_name = " ".join(assistant_role_name.split(" ")[1:])
        for user_idx, user_role_name in enumerate(user_roles):
            user_role_name = " ".join(user_role_name.split(" ")[1:])
            # Load the task list assigned for assistant and user roles
            with open((f"./ai_society_results/tasks/"
                       f"{assistant_role_name}_{user_role_name}.txt"),
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
                if not os.path.exists(f"./camel_data/ai_society/{id}.json"):
                    pool.apply_async(
                        generate_data,
                        (assistant_idx, assistant_role_name, user_idx,
                         user_role_name, task_idx, task_prompt, verbose))

                    # generate_data(assistant_idx, assistant_role_name
                    # , user_idx,
                    # user_role_name, task_idx, task_prompt)

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
