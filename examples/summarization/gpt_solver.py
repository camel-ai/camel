import concurrent.futures
import json
import os
from typing import Dict

from camel.agents import ChatAgent
from camel.messages import AssistantSystemMessage, UserChatMessage

# Directory containing your json files of CAMEL conversations
# This code will append a new key called "gpt_solution" to each json file
# Containing GPT solution to the specified task in the json file

# dir_files = "./camel_data/ai_society_solution_extraction_plus_gpt_solution"
data_dir = "./camel_data/ai_society_solution_extraction"
save_dir = "./camel_data/ai_society_solution_extraction_save"


def process_file(data: Dict[str, str]) -> None:
    print(data["id"])
    assistant_sys_msg = AssistantSystemMessage(
        role_name="Assistant",
        content="You are a helpful assistant.",
    )
    agent = ChatAgent(assistant_sys_msg)
    agent.reset()

    prompt = "Solve the following task:\n" + data["specified_task"]
    user_msg = UserChatMessage(role_name="User", content=prompt)
    assistant_msg, _, _ = agent.step(user_msg)
    print(assistant_msg[0].content)

    # Append solution to JSON file as "gpt_solution"
    data["gpt_solution"] = assistant_msg[0].content

    # create save_dir if not exists
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # save result as json file
    with open(os.path.join(save_dir, data["id"] + ".json"), 'w') as f:
        json.dump(data, f)


def main():
    # read all json files in data_dir
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]

    # load all json files as data list
    data_list = []
    for file in files:
        with open(os.path.join(data_dir, file)) as f:
            data_list.append(json.load(f))

    # Specify number of processes with max_workers argument (default: 16)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = []
        for data in data_list:
            futures.append(executor.submit(process_file, data))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Exception occurred: {e}")


if __name__ == "__main__":
    main()
