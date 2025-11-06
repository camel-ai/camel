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

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
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
1. **Markdown2doc**
   - **Description:** Convert markdown text to different file
     formats (pdf, docx, doc, html), based on Pandoc.
   - **Tools:**
     - Convert markdown text to different file formats (pdf, docx, 
     doc, html, html5)

2. **Discord**
   - **Description:** Discord is a VoIP and instant messaging 
   social platform.
   - **Tools:**
     - Get information about a Discord server (guild)
     - Get a list of members in a server
     - Create a new text channel
     - Add a reaction emoji to a message
     - Send a text message to a specific Discord channel
     - Read recent messages from a Discord channel

3. **YouTube**
   - **Description:** Extract and convert YouTube video information to 
   markdown format.
   - **Tools:**
     - Retrieve the transcript/subtitles for a YouTube video and convert 
     it to markdown

.....

========================================================================

Server Instance Creation Result:
A new Klavis AI MCP server instance has been successfully created for the 
server named **GitHub**. Here are the details:

- **Server URL:** [https://github-mcp-server.klavis.ai/sse?instance_id=
{instance_id}](https://github-mcp-server.klavis.ai/sse?instance_id={instance_id})
- **Instance ID:** {instance_id}

You can use this URL to connect to the server instance. If you need any further
assistance or actions, feel free to ask!

=========================================================================

Server Instance Details:
Here are the details about the server instance we just created:

- **Instance ID:** {instance_id}
- **Server Name:** GitHub
- **Platform:** `<your-platform-name>`
- **External User ID:** user123
- **Is Authenticated:** No

The instance is currently not authenticated. If you need to set an 
authentication token or perform any other actions, please let me know!
"""
