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

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.prompts.prompt_templates import PromptTemplateGenerator
from camel.types import ModelPlatformType, ModelType
from camel.types.enums import RoleType, TaskType

parser = argparse.ArgumentParser(
    description="Arguments for video description."
)
parser.add_argument(
    "--video_path",
    type=str,
    help="Path to the video for video description.",
    required=True,
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for video description.",
    required=False,
    default=ModelType.GPT_4O.value,
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
        "Output path for LLM video description. "
        "If not specified, results will be printed out."
    ),
    required=False,
    default=None,
)

args = parser.parse_args()


def describe_video(
    video_path: str,
    model_type: ModelType,
    temperature: float,
    output_path: str | None,
):
    # Define system message
    sys_msg_prompt = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.VIDEO_DESCRIPTION, RoleType.ASSISTANT
    )
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_msg_prompt,
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=model_type,
        model_config_dict=ChatGPTConfig(temperature=temperature).__dict__,
    )
    camel_agent = ChatAgent(sys_msg, model=model)

    # Load video into bytes
    with open(video_path, "rb") as video_file:
        video_bytes = video_file.read()

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content=(
            "These are frames from a video that I want to upload. "
            "Generate a compelling description that I can upload "
            "along with the video."
        ),
        video_bytes=video_bytes,
    )

    # Get response information
    response = camel_agent.step(user_msg)
    if output_path is None:
        print(response.msgs[0].content)
    else:
        with open(output_path, "w") as f:
            f.write(response.msgs[0].content)


def main() -> None:
    describe_video(
        args.video_path,
        ModelType(args.model_type),
        args.temperature,
        args.output_path,
    )


if __name__ == "__main__":
    main()

"""
# The video from YouTube can be found at the following link:
# https://www.youtube.com/watch?v=kQ_7GtE529M
===============================================================================
Title: "Survival in the Snow: A Bison's Battle Against Wolves" 
Description:
Witness the raw power of nature in this gripping video showcasing a dramatic 
encounter between a lone bison and a pack of wolves in a snowy wilderness. As 
the harsh winter blankets the landscape, the struggle for survival 
intensifies. Watch as the bison, isolated from its herd, faces the relentless
pursuit of hungry wolves. The tension escalates as the wolves coordinate 
their attack, attempting to overcome the bison with their numbers and 
strategic movements. Experience the breathtaking and brutal moments of this 
wildlife interaction, where every second is a fight for survival. This video 
captures the fierce beauty and the stark realities of life in the wild. Join 
us in observing these incredible animals and the instinctual battles that 
unfold in the heart of winter's grasp.
===============================================================================
"""
