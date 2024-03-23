# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
import os
import random

from camel.agents import ChatAgent
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.types import ModelType, RoleType, TaskType

QUERY_TYPE_LIST = ["extremely long-tail", "long-tail", "common"]
QUERY_LENGTH_LIST = ["less than 5 words", "5 to 15 words", "at least 10 words"]
CLARITY_LIST = ["clear", "understandable with some effort", "ambiguous"]
NUM_WORDS_LIST = ["50", "100", "200", "300", "400", "500"]
DIFFICULTY_LIST = ["high school", "college", "PhD"]
DEFAULT_LANGUAGE = "English"


def main() -> None:
    with open("./embedding_data/tasks/tasks.txt", "r") as file:
        tasks = file.readlines()
        tasks = [task.replace("\n", "") for task in tasks]

    sys_msg_generator = SystemMessageGenerator(task_type=TaskType.EMBEDDING)
    for i, task in enumerate(tasks):
        query_type = random.choice(QUERY_TYPE_LIST)
        query_length = random.choice(QUERY_LENGTH_LIST)
        clarity = random.choice(CLARITY_LIST)
        num_words = random.choice(NUM_WORDS_LIST)
        difficulty = random.choice(DIFFICULTY_LIST)
        assistant_sys_msg = sys_msg_generator.from_dict(
            meta_dict=dict(
                task=task,
                query_type=query_type,
                query_length=query_length,
                clarity=clarity,
                num_words=num_words,
                difficulty=difficulty,
            ),
            role_tuple=("Text retrieval example writer:", RoleType.ASSISTANT))
        user_msg = BaseMessage.make_user_message(role_name="User",
                                                 content="Start to generate!")
        assistant_agent = ChatAgent(
            system_message=assistant_sys_msg,
            model_type=ModelType.GPT_3_5_TURBO,
        )
        print(f"Generating positive and negative documents for '{task}'")
        assistant_response = assistant_agent.step(user_msg)
        content = assistant_response.msg.content
        try:
            data = json.loads(content)
            os.makedirs("./embedding_data/tasks/", exist_ok=True)
            with open(f"./embedding_data/tasks/{i}.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error raised during generation of task {task}", e)


if __name__ == "__main__":
    main()
