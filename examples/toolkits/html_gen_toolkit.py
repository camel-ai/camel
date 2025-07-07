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
# ruff: noqa: E501
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HtmlGenToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0},
)

# Define system message for the agent
sys_msg = "You are a helpful assistant that can create and modify files."

# Set up output directory
output_dir = "./file_write_outputs"
os.makedirs(output_dir, exist_ok=True)

# Initialize the FileWriteToolkit with the output directory
html_toolkit = HtmlGenToolkit(workspace=output_dir)
# Get the tools from the toolkit
tools_list = html_toolkit.get_tools()

# Initialize a ChatAgent with the tools
camel_agent = ChatAgent(
    system_message=sys_msg, model=model, tools=tools_list, max_iteration=1
)

query = """Please generate a for a ppt slide. the style can be purple 
and gold. the slide is about the benefits of AI and you can generate a chart 
to show the benefits. and add a image to the slide.the image is 
https://ghli.org/camel/wechat.png,its our community logo welcome to join us.
"""

camel_agent.reset()
response = camel_agent.step(query)
print(response.msgs[0].content)

"""
===============================================================================
I have generated a PPT slide about the benefits of AI with a purple and gold 
style. The slide includes a chart showing the key benefits and an image of 
your community logo with a welcome message. The slide is saved as an HTML file 
named "benefits_of_ai_slide.html". You can open this file in a web browser to 
view the slide. If you need the slide in another format or any other 
modifications, please let me know!
===============================================================================
"""
