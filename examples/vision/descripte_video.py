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

from camel.agents import ChatAgent
from camel.generators import PromptTemplateGenerator
from camel.messages import BaseMessage
from camel.types import ModelType, RoleType, TaskType

parser = argparse.ArgumentParser(description="Arguments for video description.")
parser.add_argument(
    "--video_path",
    type=str,
    help="Path to the video for description.",
    required=True,
)


def descripte_video(video_path: str) -> None:
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.DESCRIPTE_VIDEO, RoleType.ASSISTANT
    )

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_msg,
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model_type=ModelType.GPT_4_TURBO,
    )
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="These are frames from a video that I want to upload. Generate a compelling description that I can upload along with the video.",
        video_path=video_path,
    )
    assistant_response = agent.step(user_msg)
    print("=" * 20 + " RESULT " + "=" * 20)
    print(assistant_response.msgs[0].content)
    print("=" * 48)


def main(args: argparse.Namespace) -> None:
    descripte_video(args.video_path)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
