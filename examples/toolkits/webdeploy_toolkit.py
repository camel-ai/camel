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
from camel.models import ModelFactory
from camel.toolkits import WebDeployToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0},
)

# Define system message for the agent
sys_msg = "You are a helpful assistant that can deploy web server."

# Initialize the WebDeployToolkit
web_deploy_toolkit = WebDeployToolkit()
# Get the tools from the toolkit
tools_list = web_deploy_toolkit.get_tools()

# Initialize a ChatAgent with the tools
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools_list,
)

# Example 1: deploy a simple web server,which can play snake game.
query = """use toolkit writing html to deploy a 
simple web server,which can play snake game.deploy it in port 8005"""

camel_agent.reset()
response = camel_agent.step(query)
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

"""
==========================================================================
I have deployed a simple web server that hosts a Snake game. You can play 
the game by opening the following URL in your web browser: 
http://localhost:8000

Use the arrow keys to control the snake. Enjoy the game!
==========================================================================
"""
