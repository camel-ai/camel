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
from camel.generators import PromptTemplateGenerator
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import (
    ModelPlatformType,
    ModelType,
    RoleType,
    TaskType,
)

parser = argparse.ArgumentParser(description="Arguments for object detection.")
parser.add_argument(
    "--image_paths",
    metavar='N',
    type=str,
    nargs='+',
    help="Path to the images for object detection.",
    default=None,
    required=True,
)


def detect_image_obj(image_paths: str) -> None:
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.OBJECT_RECOGNITION, RoleType.ASSISTANT
    )
    print("=" * 20 + " SYS MSG " + "=" * 20)
    print(sys_msg)
    print("=" * 49)

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_msg,
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model=model,
    )
    image_list = [Image.open(image_path) for image_path in image_paths]

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Please start the object detection for following image!",
        image_list=image_list,
        image_detail="high",
    )
    assistant_response = agent.step(user_msg)
    print("=" * 20 + " RESULT " + "=" * 20)
    print(assistant_response.msgs[0].content)
    print("=" * 48)


def main(args: argparse.Namespace) -> None:
    detect_image_obj(args.image_paths)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args=args)
