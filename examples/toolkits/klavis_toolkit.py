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
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import KlavisToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = """You are a helpful AI assistant that can use Klavis API tools
to manage MCP server instances and perform various server-related tasks.
When using tools, first list the available servers using get_all_servers,
then use the appropriate tool based on the task. Always provide clear
explanations of what you're doing."""

# Set model config
tools = KlavisToolkit().get_tools()
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# First, list all available servers
usr_msg = "List all available MCP servers."
response = camel_agent.step(usr_msg)
print("Available MCP Servers:")
print(response.msg.content)
print("\n" + "=" * 80 + "\n")

# Create a new server instance
usr_msg = """Now, create a new Klavis AI MCP server instance.
Use the server name 'GitHub', user ID 'user123', and platform
name '<your-platform-name>'."""
response = camel_agent.step(usr_msg)
print("Server Instance Creation Result:")
print(response.msg.content)
print("\n" + "=" * 80 + "\n")

# Get details about the created server instance
usr_msg = """Get details about the server instance we just created.
Use the instance_id returned from the previous response."""
response = camel_agent.step(usr_msg)
print("Server Instance Details:")
print(response.msg.content)

"""
Expected output would show:
1. A list of available MCP servers with their details
2. The result of creating a new server instance (success or error)
3. Details about the created server instance

The actual responses will depend on:
- Whether valid API keys are configured in the environment
- The actual server data available in the Klavis API
- Success/failure of the API calls
"""
