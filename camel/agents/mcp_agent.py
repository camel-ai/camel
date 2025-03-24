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

SYS_PROMPT = """
You are a helpful assistant, and you prefer to use tools prvided by the user 
to solve problems.
Using a tool, you will tell the user `server_idx`, `tool_name` and 
`tool_args` formated in JSON as following:
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
        model_fc_available: bool = False,
    ) -> None:
        r"""Initialize the MCP agent.

        Args:
            model (Optional[BaseModelBackend]): Model backend for the agent.
                (default: :obj:`None`)
            model_fc_available (bool): Flag indicating whether the .
                (default: :obj:`False`)

        """
        if model_fc_available:
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
        self._model_fc_available = model_fc_available
        self._text_tools = None

    async def connect(self):
        await self._mcp_toolkit.connect()

    async def close(self):
        await self._mcp_toolkit.disconnect()

    def add_mcp_tools(self):
        assert self._mcp_toolkit.is_connected(), "Server is not connected."
        prompt = TextPrompt(TOOLS_PROMPT)
        self._text_tools = prompt.format(
            tools=self._mcp_toolkit.get_text_tools()
        )
        if self._model_fc_available:
            tools = self._mcp_toolkit.get_tools()
            for tool in tools:
                self.add_tool(tool)

    async def get_text_tools(self):
        assert self._mcp_toolkit.is_connected(), "Server is not connected."
        await self.add_mcp_tools()
        return self._text_tools

    async def run(
        self,
        prompt: str,
    ):
        assert self._mcp_toolkit.is_connected(), "Server is not connected."
        if self._model_fc_available:
            response = await self.astep(prompt)
            return response
        else:
            task = f"## Task:\n  {prompt}"
            response = await self.astep(self._text_tools + task)
            content = response.msgs[0].content.lower()

            tool_calls = []
            while "```json" in content:
                json_start = re.search(r'```json', content).span()[1]
                json_end = re.search(r'```', content[json_start:]).span()[0]
                json_end = json_end + json_start
                tool_josn = content[json_start:json_end].strip('\n')
                tool_calls.append(json.loads(tool_josn))
                content = content[json_end:]

            if len(tool_calls) == 0:
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
