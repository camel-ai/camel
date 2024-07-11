import os
import json
from camel.agents import ChatAgent
from camel.configs import GeminiConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

from huggingface_hub import snapshot_download

SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

DATASET_DIR = os.path.join(SCRIPT_DIR, "Dataset")

def get_gaia():
    r"""
    Please using huggingface-cli login to get authorization
    From Hugging Face download GAIA dataset
    This function will create a folder to cache GAIA dataset
    """

    if not os.path.isdir(DATASET_DIR):
        os.mkdir(DATASET_DIR)
    snapshot_download(
        repo_id="gaia-benchmark/GAIA",
        repo_type="dataset",
        local_dir= DATASET_DIR,
        local_dir_use_symlinks=True,
    )

def main():
    get_gaia()
    validation = os.path.join(DATASET_DIR, "2023", "validation")
    test = os.path.join(DATASET_DIR, "2023", "test")
    validation_tasks = [[],[],[]]
    with open(os.path.join(validation, "metadata.jsonl")) as f:
        for line in f:
            data = json.loads(line)
            validation_tasks[data["Level"] - 1].append(data)
    
    test_tasks = [[],[],[]]
    with open(os.path.join(test, "metadata.jsonl")) as f:
        for line in f:
            data = json.loads(line)
            if data["task_id"] == "0-0-0-0-0":
                continue
            test_tasks[data["Level"] - 1].append(data)
    
    # prepare prompts
    task_prompt = (
    """
    You are a general AI assistant. I will ask you a question. Report your thoughts, and
    finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].
    YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated
    list of numbers and/or strings.
    If you are asked for a number, don’t use comma to write your number neither use units such as $ or
    percent sign unless specified otherwise.
    If you are asked for a string, don’t use articles, neither abbreviations (e.g. for cities), and write the
    digits in plain text unless specified otherwise.
    If you are asked for a comma separated list, apply the above rules depending of whether the element
    to be put in the list is a number or a string.""".strip()
    )

    gaia_question = validation_tasks[0][1]['Question']
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_1_5_PRO,
        model_config_dict=GeminiConfig(temperature=0.2).__dict__,
    )
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=task_prompt,
    )

    # Set agent
    camel_agent = ChatAgent(system_message=sys_msg, model=model)

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content= gaia_question,
    )
    response = camel_agent.step(user_msg)
    print(response.msgs[0].content)
    print(validation_tasks[0][1]['Final answer'])
    print(gaia_question)



if __name__ == "__main__":
    main()
