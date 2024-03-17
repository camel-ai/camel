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
import argparse

from PIL import Image

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.generators import PromptTemplateGenerator
from camel.messages import BaseMessage
from camel.types import ModelType, RoleType, TaskType

parser = argparse.ArgumentParser(description="Arguments for object detection.")
parser.add_argument(
    "--image_path",
    type=str,
    help="Path to the image for object detection.",
)


def get_assistant_agent() -> ChatAgent:
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.OBJECT_DETECTION, RoleType.ASSISTANT)
    print("=" * 20 + " SYS MSG " + "=" * 20)
    print(sys_msg)
    print("=" * 49)

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_msg,
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model_type=ModelType.GPT_4_TURBO_VISION,
        model_config=ChatGPTConfig(max_tokens=4096),
    )
    return agent


def detect(agent: ChatAgent, image_path: str) -> None:
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Please start the object detection for following image!",
        image=Image.open(image_path),
    )
    assistant_response = agent.step(user_msg)
    print("=" * 20 + " RESULT " + "=" * 20)
    print(assistant_response.msgs[0].content)
    print("=" * 48)


def main(args: argparse.Namespace) -> None:
    agent = get_assistant_agent()
    detect(agent, args.image_path)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args=args)
