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
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import ImageAnalysisToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

image_analysis_toolkit = ImageAnalysisToolkit(model=model)

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[*image_analysis_toolkit.get_tools()],
)


user_msg = BaseMessage.make_user_message(
    role_name="User",
    content='''
        The image link is: https://upload.wikimedia.org/wikipedia/commons/
        thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/
        2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg
        What's in this image? You must use image analysis to help me.
        ''',
)
response = agent.step(user_msg)
print(response.msgs[0].content)
""""
===========================================================================
The image depicts a serene landscape featuring a wooden boardwalk that leads 
through a lush, green marsh or meadow. The boardwalk is centrally positioned, 
extending into the distance and inviting viewers to imagine walking along it. 
On either side of the boardwalk, tall grass and various vegetation create a 
vibrant green expanse.

In the background, there are clusters of trees and shrubs, adding depth to the 
scene. The sky above is mostly clear with a few scattered clouds, showcasing a 
gradient of blue hues. The overall atmosphere is tranquil and natural, 
suggesting a peaceful outdoor setting, with soft lighting that likely 
indicates early morning or late afternoon."
============================================================================
"""
