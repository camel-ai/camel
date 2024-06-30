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
from __future__ import annotations

import argparse

from PIL import Image

from camel.agents import ChatAgent
from camel.generators import PromptTemplateGenerator
from camel.messages import BaseMessage
from camel.models import OpenAIModel
from camel.types import ModelType, OpenAIVisionDetailType, RoleType, TaskType

parser = argparse.ArgumentParser(
    description="Arguments for object recognition."
)
parser.add_argument(
    "--image_path",
    type=str,
    help="Path to the image for object recognition.",
    required=True,
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for object recognition.",
    required=False,
    default=ModelType.GPT_4O.value,
)
parser.add_argument(
    "--image_detail",
    type=str,
    help="Image detail for object recognition.",
    required=False,
    choices=["high", "low", "auto"],
    default=OpenAIVisionDetailType.HIGH.value,
)
parser.add_argument(
    "--temperature",
    type=float,
    help="Model temperature.",
    required=False,
    default=1.0,
)
parser.add_argument(
    "--output_path",
    type=str,
    help=(
        "Output path for LLM object recognition. "
        "If not specified, results will be printed out."
    ),
    required=False,
    default=None,
)

args = parser.parse_args()


def detect_image_obj(
    image_path: str,
    model_type: ModelType,
    image_detail: OpenAIVisionDetailType,
    temperature: float,
    output_path: str | None,
) -> None:
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.OBJECT_RECOGNITION, RoleType.ASSISTANT
    )
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_msg,
    )
    model = OpenAIModel(
        model_type=model_type, model_config_dict={"temperature": temperature}
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model=model,
    )
    images = [Image.open(image_path)]
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Please start the object recognition for following image!",
        image_list=images,
        image_detail=image_detail,
    )
    assistant_response = agent.step(user_msg)
    if output_path is None:
        print(assistant_response.msgs[0].content)
    else:
        with open(output_path, "w") as f:
            f.write(assistant_response.msgs[0].content)


def main() -> None:
    detect_image_obj(
        args.image_path,
        ModelType(args.model_type),
        OpenAIVisionDetailType(args.image_detail),
        args.temperature,
        args.output_path,
    )


if __name__ == "__main__":
    main()
