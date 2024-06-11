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
from camel.agents import ChatAgent
import argparse
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.prompts.prompt_templates import PromptTemplateGenerator
from camel.types import ModelType
from camel.types.enums import RoleType, TaskType

# 
parser = argparse.ArgumentParser(description="Arguments for video description.")
parser.add_argument(
    "--video_path",
    type=str,
    help="Path to the video for description.",
    required=True,
)

# Define system message
sys_msg_prompt = PromptTemplateGenerator().get_prompt_from_key(
    TaskType.DESCRIPTE_VIDEO, RoleType.ASSISTANT
)
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content=sys_msg_prompt,
)

# Set model config
model_config = ChatGPTConfig(
    temperature=0.0,
)

# Set agent
camel_agent = ChatAgent(
    sys_msg,
    model_config=model_config,
    model_type=ModelType.GPT_4_TURBO,
)
camel_agent.reset()

# Define a user message
video_bytes = b""

video_path = parser.parse_args().video_path
with open(video_path, "rb") as video_file:
    video_bytes = video_file.read()
user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="These are frames from a video that I want to upload. Generate a"
    "compelling description that I can upload along with the video.",
    video_bytes=video_bytes,
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
Title: "Journey of Resilience: A Tale of Determination and Triumph"

Description:
Dive into the gripping narrative of "Journey of Resilience,"
a cinematic exploration of the human spirit's capacity to overcome adversity. 
This video captures the intense and emotional journey of a man who faces the 
crossroads of life, symbolized by a desolate highway and the relentless pursuit
of his goals. Witness his raw determination as he sprints through the vast, 
unforgiving landscape, each step echoing his inner turmoil and resolve.

The narrative unfolds with powerful imagery, from the intense focus in his eyes
to the symbolic scenes of struggle and contemplation in a water-filled 
bathtub, portraying the depths of his challenges. A mentor figure appears, 
guiding and pushing him beyond his limits, emphasizing the universal theme of 
growth through guidance and perseverance.

As the story progresses, the protagonist is seen preparing for a boxing match, 
symbolizing his fight against life's obstacles. The climax in the boxing ring 
serves as a metaphor for facing his toughest challenges head-on, surrounded by 
an audience that represents societal pressures and expectations.

This video is not just a portrayal of physical strength but a deeper 
commentary on the psychological battles one must endure and overcome. It's a 
reminder that the hardest parts of our journeys are often what lead us to our 
greatest victories.

Join us in this visually stunning and emotionally charged journey that will 
inspire you to push through your limits and emerge victorious, no matter the 
challenges ahead.
===============================================================================
"""
