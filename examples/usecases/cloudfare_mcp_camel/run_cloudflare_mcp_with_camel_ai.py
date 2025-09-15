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
from camel.toolkits import MCPToolkit
import dotenv
import os

dotenv.load_dotenv()

sys_msg = BaseMessage(
    role_name="cloudfare assistant",
    role_type="assistant",
    meta_dict={},
    content="You are a helpful assistant that can access Cloudflare's documentation via MCP"
)


# Initialize the model (using Anthropic's Claude as an example)
model = ModelFactory.create(
    model_platform="gemini",
    model_type="gemini-2.5-pro-preview-05-06",
    api_key=os.getenv("GEMINI_API_KEY"),
    model_config_dict={"temperature": 0.5, "max_tokens": 4096},
    )

#configure the mcp camel toolkit with the path of the config file
mcp_toolkit = MCPToolkit(config_path="mcp_config.json")

# Get the tools from the toolkit
mcp_tools = mcp_toolkit.get_tools()

# Create the ChatAgent with the system message, model, and toolkit
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=mcp_tools,
)

# Example interaction with the agent
user_msg = "list me the index of the documentation?"
response = agent.step(user_msg)
print(response)