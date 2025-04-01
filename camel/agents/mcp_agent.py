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

import json
from typing import List, Optional

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.prompts import TextPrompt
from camel.toolkits import MCPToolkit
from camel.types import RoleType

# AgentOps decorator setting
try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent

logger = get_logger(__name__)


# Define pydantic model for structured tool call response
class MCPArgument(BaseModel):
    arg_name: str = Field(description="Name of the argument")
    arg_value: str = Field(description="Value of the argument")


class MCPToolCall(BaseModel):
    server_idx: int = Field(description="Index of the server to use")
    tool_name: str = Field(description="Name of the tool to call")
    tool_args: List[MCPArgument] = Field(
        description="Arguments to pass to the tool"
    )


SYS_PROMPT = """
You are a helpful assistant, and you prefer to use tools prvided by the user 
to solve problems.
Using a tool, you will tell the user `server_idx`, `tool_name` and 
`tool_args` formated in JSON as following:
```json
{
    "server_idx": idx,
    "tool_name": "tool_name",
    "tool_args": [
        {"arg_name": "arg1", "arg_value": "value1"},
        {"arg_name": "arg2", "arg_value": "value2"},
        ...
    ]
}
```
Otherwise, you should respond to the user directly.
"""


TOOLS_PROMPT = """
## Available Tools:

{tools}
"""

FINAL_RESPONSE_PROMPT = """
The result `{results}` is provided by tools you proposed.
Please answer me according to the result directly.
"""


@track_agent(name="MCPAgent")
class MCPAgent(ChatAgent):
    def __init__(
        self,
        config_path: str,
        model: Optional[BaseModelBackend] = None,
        model_function_call_available: bool = False,
    ) -> None:
        r"""Initialize the MCP agent.

        The MCP (Model Context Protocol) Agent provides an interface for LLMs
        to interact with tools using the Model Context Protocol. This
        agent can operate in two modes: with function calling capabilities or
        with text-based tool descriptions.

        Args:
            config_path (str): Path to the JSON configuration file defining
                MCP servers.
            model (Optional[BaseModelBackend]): Model backend for the agent.
                (default: :obj:`None`)
            model_function_call_available (bool): Flag indicating whether the
                model supports function calling capabilities. When True, tools
                are provided directly to the model; when False, tools are
                described in text format. (default: :obj:`False`)

        References:
            For more information on the Model Context Protocol (MCP), see the
            MCPToolkit implementation which provides a unified interface for
            managing multiple MCP server connections and their tools.
        """
        if model_function_call_available:
            sys_prompt = "You are a helpful assitant."
        else:
            sys_prompt = SYS_PROMPT

        system_message = BaseMessage(
            role_name="MPCRouter",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content=sys_prompt,
        )

        super().__init__(system_message, model=model)

        self._mcp_toolkit = MCPToolkit(config_path=config_path)
        self._model_function_call_available = model_function_call_available
        self._text_tools = None

    async def connect(self):
        await self._mcp_toolkit.connect()

    async def close(self):
        await self._mcp_toolkit.disconnect()

    def add_mcp_tools(self):
        if not self._mcp_toolkit.is_connected():
            raise ConnectionError("Server is not connected.")
        prompt = TextPrompt(TOOLS_PROMPT)
        self._text_tools = prompt.format(
            tools=self._mcp_toolkit.get_text_tools()
        )
        if self._model_function_call_available:
            tools = self._mcp_toolkit.get_tools()
            for tool in tools:
                self.add_tool(tool)

    async def get_text_tools(self):
        if not self._mcp_toolkit.is_connected():
            raise ConnectionError("Server is not connected.")
        await self.add_mcp_tools()
        return self._text_tools

    async def run(
        self,
        prompt: str,
    ):
        if not self._mcp_toolkit.is_connected():
            raise ConnectionError("Server is not connected.")

        if self._model_function_call_available:
            response = await self.astep(prompt)
            return response
        else:
            task = f"## Task:\n  {prompt}"

            # Send the prompt with tools description and use MCPToolCall as
            # response_format
            response = await self.astep(
                str(self._text_tools) + task, response_format=MCPToolCall
            )

            # Add type checking to handle the case when parsed is None or not
            # of expected type
            if response.msgs[0].parsed is None or not isinstance(
                response.msgs[0].parsed, MCPToolCall
            ):
                raise ValueError("Failed to parse response as MCPToolCall")

            server_idx = response.msgs[0].parsed.server_idx
            tool_name = response.msgs[0].parsed.tool_name
            tool_args = response.msgs[0].parsed.tool_args

            # Convert MCPArgument list to dictionary for MCP server
            tool_args_dict = {arg.arg_name: arg.arg_value for arg in tool_args}

            server = self._mcp_toolkit.servers[server_idx]
            result = await server.call_tool(tool_name, tool_args_dict)

            tools_results = [{tool_name: result.content[0].text}]
            results = json.dumps(tools_results)

            final_prompt = TextPrompt(FINAL_RESPONSE_PROMPT).format(
                results=results
            )
            response = await self.astep(final_prompt)

            return response
