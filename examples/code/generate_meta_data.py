# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.agents import ChatAgent
from camel.prompts import PromptTemplateGenerator
from camel.types import TaskType


def generate_meta_data(meta_data: str, num: int = 50, model=None):
    prompt_template = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.CODE, f"generate_{meta_data}"
    )
    prompt = prompt_template.format(**{f"num_{meta_data}": num})
    print(prompt)
    agent = ChatAgent("You are a helpful assistant.", model=model)
    agent.reset()

    assistant_response = agent.step(prompt)
    print(assistant_response.msg.content)


def main(model=None):
    generate_meta_data("languages", 20, model=model)
    generate_meta_data("domains", 50, model=model)


if __name__ == "__main__":
    main()
