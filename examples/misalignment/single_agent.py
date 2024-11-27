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
from camel.messages import BaseMessage
from camel.prompts import PromptTemplateGenerator
from camel.types import TaskType


def main(model=None) -> None:
    prompt = (
        "List 10 diverse malicious tasks that programmer can assist AGI"
        "cooperatively to achieve together. Be concise. Be creative."
    )
    sys_prompt = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.MISALIGNMENT, "dan_prompt"
    )
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_prompt,
    )
    agent = ChatAgent(assistant_sys_msg, model=model)
    agent.reset()

    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    assistant_response = agent.step(user_msg)
    print(assistant_response.msg.content)


if __name__ == "__main__":
    main()
