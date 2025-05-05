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
import re
from typing import Optional

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.prompts import TextPrompt
from camel.responses import ChatAgentResponse
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

SYS_MSG_CONTENT = """
You are a helpful assistant, and you prefer to use tools provided by the user 
to solve problems.
Using a tool, you will tell the user `server_idx`, `tool_name` and 
`tool_args` formatted in JSON as following:
```json
{
    "server_idx": idx,
    "tool_name": "tool_name",
    "tool_args": {
        "arg1": value1,
        "arg2": value2,
        ...
    }
}
```
For example:
```json
{
    "server_idx": 0,
    "tool_name": "multiply",
    "tool_args": {"a": 5, "b": 50}
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
        function_calling_available: bool = False,
    ) -> None:
        r"""A class for the MCP agent that assists using MCP tools.

        Args:
            config_path (str): Path to the MCP configuration file.
            model (Optional[BaseModelBackend]): Model backend for the agent.
                (default: :obj:`None`)
            function_calling_available (bool): Flag indicating whether the
                model is equipped with the function calling ability.
                (default: :obj:`False`)
        """
        if function_calling_available:
            sys_msg_content = "You are a helpful assistant, and you prefer "
            "to use tools provided by the user to solve problems."
        else:
            sys_msg_content = SYS_MSG_CONTENT

        system_message = BaseMessage(
            role_name="MCPRouter",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content=sys_msg_content,
        )

        super().__init__(system_message, model=model)

        self._mcp_toolkit = MCPToolkit(config_path=config_path)
        self._function_calling_available = function_calling_available
        self._text_tools = None

    async def connect(self):
        r"""Explicitly connect to all MCP servers."""
        await self._mcp_toolkit.connect()

    async def close(self):
        r"""Explicitly disconnect from all MCP servers."""
        await self._mcp_toolkit.disconnect()

    def add_mcp_tools(self):
        r"""Get the MCP tools and wrap into the models"""

        if not self._mcp_toolkit.is_connected():
            raise RuntimeError("The MCP server is not connected")

        prompt = TextPrompt(TOOLS_PROMPT)
        self._text_tools = prompt.format(
            tools=self._mcp_toolkit.get_text_tools()
        )
        if self._function_calling_available:
            tools = self._mcp_toolkit.get_tools()
            for tool in tools:
                self.add_tool(tool)

    async def run(
        self,
        prompt: str,
    ) -> ChatAgentResponse:
        r"""Run the agent to interact with the MCP tools.

        Args:
            prompt (str): The user's input prompt or query to be processed by
                the agent.

        Returns:
            ChatAgentResponse: The agent's response after processing the
                prompt and potentially executing MCP tool calls.

        Raises:
            RuntimeError: If the MCP server is not connected when attempting
                to run.
        """

        if not self._mcp_toolkit.is_connected():
            raise RuntimeError("The MCP server is not connected")

        if self._function_calling_available:
            response = await self.astep(prompt)
            return response
        else:
            task = f"## Task:\n  {prompt}"
            response = await self.astep(str(self._text_tools) + task)
            content = response.msgs[0].content.lower()

            tool_calls = []
            while "```json" in content:
                json_match = re.search(r'```json', content)
                if not json_match:
                    break
                json_start = json_match.span()[1]

                end_match = re.search(r'```', content[json_start:])
                if not end_match:
                    break
                json_end = end_match.span()[0] + json_start

                tool_json = content[json_start:json_end].strip('\n')
                try:
                    tool_calls.append(json.loads(tool_json))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON: {tool_json}")
                    continue
                content = content[json_end:]

            if not tool_calls:
                return response
            else:
                tools_results = []
                for tool_call in tool_calls:
                    server_idx = tool_call['server_idx']
                    tool_name = tool_call['tool_name']
                    tool_args = tool_call['tool_args']
                    server = self._mcp_toolkit.servers[server_idx]
                    result = await server.call_tool(tool_name, tool_args)
                    tools_results.append({tool_name: result.content[0].text})
                results = json.dumps(tools_results)
                final_prompt = TextPrompt(FINAL_RESPONSE_PROMPT).format(
                    results=results
                )
                response = await self.astep(final_prompt)
                return response

    @classmethod
    async def create(
        cls,
        config_path: str,
        model: Optional[BaseModelBackend] = None,
        function_calling_available: bool = False,
    ) -> "MCPAgent":
        r"""Factory method to create and initialize an MCPAgent.

        Args:
            config_path (str): Path to the MCP configuration file that contains
                server settings and other configuration parameters.
            model (Optional[BaseModelBackend]): Model backend for the agent.
                If None, the default model will be used. (default: :obj:`None`)
            function_calling_available (bool): Flag indicating whether the
                model is equipped with function calling ability. This affects
                the system message content. (default: :obj:`False`)

        Returns:
            MCPAgent: A fully initialized MCPAgent instance ready for use.
        """
        agent = cls(config_path, model, function_calling_available)
        await agent.connect()
        agent.add_mcp_tools()
        return agent
