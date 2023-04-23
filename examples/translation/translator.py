import codecs
import json
import multiprocessing
import os

from camel.agents import ChatAgent
from camel.generators import SystemMessageGenerator
from camel.messages import UserChatMessage
from camel.typing import ModelType, RoleType, TaskType


def translate_content(directory_path: str, file_path: str,
                      language: str) -> None:

    # File_path of the .json file to translate we extract the name for saving
    file_name = file_path.split("/")[-1].split(".json")[0]

    # Check that file_name.json does not exist in the target directory
    save_path = f"{directory_path}_translated/{language}/{file_name}.json"
    if os.path.exists(save_path):
        return

    # Load the json file
    with open(file_path, "r") as json_file:
        json_data = json.load(json_file)

    # Translate the content of each message in the json
    for i in range(json_data['num_messages']):

        msg_i_content = "Sentence to translate: " + json_data[
            f"message_{i+1}"]["content"]

        sys_msg_generator = SystemMessageGenerator(
            task_type=TaskType.TRANSLATION)

        assistant_sys_msg = sys_msg_generator.from_dict(
            meta_dict=dict(language=language.capitalize()),
            role_tuple=('Language Translator', RoleType.ASSISTANT))

        assistant_agent = ChatAgent(assistant_sys_msg, ModelType.GPT_3_5_TURBO)

        user_msg = UserChatMessage(role_name="Language Translator",
                                   content=msg_i_content)

        assistant_msgs, _, _ = assistant_agent.step(user_msg)
        assistant_msg = assistant_msgs[0]

        json_data[f"message_{i+1}"]["content"] = assistant_msg.content

    with codecs.open(save_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)


def main(directory_path: str) -> None:

    # List of languages to translate to
    language_list = [
        "arabic", "chinese", "french", "german", "hindi", "italian",
        "japanese", "korean", "russian", "spanish"
    ]

    # Get the language to translate based on Slurm array index
    try:
        language_index = int(os.environ["SLURM_ARRAY_TASK_ID"])
    except KeyError:
        print("SLURM_ARRAY_TASK_ID not found. Defaulting to 0 (i.e Arabic)")
        # Default to Arabic, you can change to any other language
        language_index = 0

    language = language_list[language_index]

    # Get list of all .json files paths
    json_file_paths = []

    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            file_path = os.path.join(directory_path, filename)
            json_file_paths.append(file_path)

    pool = multiprocessing.Pool()

    # Apply parallel translation to all .json files
    for file_path in json_file_paths:
        pool.apply_async(translate_content,
                         args=(directory_path, file_path, language))
    pool.close()
    pool.join()


if __name__ == "__main__":
    main(directory_path="./camel_data/ai_society")
