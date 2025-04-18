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
from camel.models import ModelFactory
from camel.prompts.prompt_templates import PromptTemplateGenerator
from camel.types import ModelPlatformType, ModelType
from camel.types.enums import RoleType, TaskType

# Define system message
sys_msg_prompt = PromptTemplateGenerator().get_prompt_from_key(
    TaskType.VIDEO_DESCRIPTION, RoleType.ASSISTANT
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set agent
camel_agent = ChatAgent(sys_msg_prompt, model=model)

# The video from YouTube can be found at the following link:
# https://www.youtube.com/watch?v=kQ_7GtE529M
video_path = "bison.mp4"
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
