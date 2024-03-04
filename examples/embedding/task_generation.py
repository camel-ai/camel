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
import os

from camel.agents import ChatAgent
from camel.generators import PromptTemplateGenerator
from camel.messages import BaseMessage
from camel.types import TaskType


def main() -> None:
    num_generate = 3
    num_tasks = 3
    prompt_template = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.EMBEDDING, "generate_tasks")
    evaluation_dict = {
        'num_tasks': num_tasks,
    }
    prompt = prompt_template.format(**evaluation_dict)
    print(prompt)
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful text retrieval task generator.",
    )
    agent = ChatAgent(assistant_sys_msg)
    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)

    total_tasks = []
    for i in range(num_generate):
        agent.reset()
        assistant_response = agent.step(user_msg)
        assistant_content = assistant_response.msg.content
        # Split tasks string to a list of tasks:
        tasks = assistant_content.split("\n")
        # Remove the start token such as "1. ":
        tasks = [task.split('. ')[1] for task in tasks]
        total_tasks = total_tasks + tasks

    os.makedirs("./embedding_data/tasks/", exist_ok=True)
    with open("./embedding_data/tasks/tasks.txt", "w") as file:
        file.write("\n".join(total_tasks))


if __name__ == "__main__":
    main()
