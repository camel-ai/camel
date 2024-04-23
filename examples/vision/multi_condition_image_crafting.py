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
from camel.types import ModelType
from camel.agents.chat_agent import ChatAgent
from camel.configs import FunctionCallingVisionConfig
from camel.generators import PromptTemplateGenerator
from camel.messages.base import BaseMessage
from camel.types import ModelType, RoleType, TaskType
from camel.functions import T2I_FUNCS

parser = argparse.ArgumentParser(description="Arguments for Image Condition.")
parser.add_argument(
    "--image_paths",
    metavar='N',
    type=str,
    nargs='+',
    help="Path to the images as conditions.",
    default=None
)


def multi_condition_image_craft(image_paths: str) -> list[str]:
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(TaskType.MULTI_CONDITION_IMAGE_CRAFT, RoleType.ASSISTANT)
    print("=" * 20 + " SYS MSG " + "=" * 20)
    print(sys_msg)
    print("=" * 49)

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Artist",
        content=sys_msg,
    )

    function_list = [*T2I_FUNCS]
    assistant_model_config = FunctionCallingVisionConfig.from_openai_function_list(
        function_list=function_list,
        kwargs=dict(temperature=0.0),
    )

    dalle_agent = ChatAgent(
        system_message=assistant_sys_msg,
        model_type=ModelType.GPT_4_TURBO_VISION,
        model_config=assistant_model_config,
        function_list=[*T2I_FUNCS],
    )

    image_list = [Image.open(image_path) for image_path in image_paths]

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Please generate an image based on the provided images and text, ensuring that the image meets the textual requirements and includes all the visual subjects from the images.",
        # TODO: Now we only use local path, and we use replace it with url in the future.
        image_list=image_list,
        image_detail="high",
    )

    response = dalle_agent.step(user_msg)

    print("=" * 20 + " RESULT " + "=" * 20)
    print(response.msg.content)
    print("=" * 48)


def main(args: argparse.Namespace) -> None:
    multi_condition_image_craft(args.image_paths)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args=args)
