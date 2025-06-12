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

import asyncio
import json
import platform
import re
from typing import Any, Callable, Dict, List, Optional, Union, cast

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.prompts import TextPrompt
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool, MCPToolkit
from camel.types import (
    BaseMCPRegistryConfig,
    MCPRegistryType,
    ModelPlatformType,
    ModelType,
    RoleType,
)

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
    r"""A specialized agent designed to interact with MCP registries.
    The MCPAgent enhances a base ChatAgent by integrating MCP tools from
    various registries for search capabilities.

    Attributes:
        system_message (Optional[str]): The system message for the chat agent.
            (default: :str:`"You are an assistant with search capabilities
            using MCP tools."`)
        model (BaseModelBackend): The model backend to use for generating
            responses. (default: :obj:`ModelPlatformType.DEFAULT` with
            `ModelType.DEFAULT`)
        registry_configs (List[BaseMCPRegistryConfig]): List of registry
            configurations (default: :obj:`None`)
        local_config (Optional[Dict[str, Any]]): The local configuration for
            the MCP agent. (default: :obj:`None`)
        local_config_path (Optional[str]): The path to the local configuration
            file for the MCP agent. (default: :obj:`None`)
        function_calling_available (bool): Flag indicating whether the
            model is equipped with the function calling ability.
            (default: :obj:`True`)
        **kwargs: Inherited from ChatAgent
    """

    def __init__(
        self,
        system_message: Optional[Union[str, BaseMessage]] = (
            "You are an assistant with search capabilities using MCP tools."
        ),
        model: Optional[BaseModelBackend] = None,
        registry_configs: Optional[
            Union[List[BaseMCPRegistryConfig], BaseMCPRegistryConfig]
        ] = None,
        local_config: Optional[Dict[str, Any]] = None,
        local_config_path: Optional[str] = None,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        function_calling_available: bool = True,
        **kwargs,
    ):
        if model is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

        if isinstance(registry_configs, BaseMCPRegistryConfig):
            self.registry_configs = [registry_configs]
        else:
            self.registry_configs = registry_configs or []

        if local_config_path:
            with open(local_config_path, 'r') as f:
                local_config = json.load(f)

        self.local_config = local_config
        self.function_calling_available = function_calling_available

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

        # Initialize the toolkit if configuration is provided
        self.mcp_toolkit = self._initialize_mcp_toolkit()

        super().__init__(
            system_message=system_message,
            model=model,
            tools=tools,
            **kwargs,
        )

    def _initialize_mcp_toolkit(self) -> MCPToolkit:
        r"""Initialize the MCP toolkit from the provided configuration."""
        config_dict = {}
        for registry_config in self.registry_configs:
            config_dict.update(registry_config.get_config())

        if self.local_config:
            config_dict.update(self.local_config)

        return MCPToolkit(config_dict=config_dict)

    def add_registry(self, registry_config: BaseMCPRegistryConfig) -> None:
        r"""Add a new registry configuration to the agent.

        Args:
            registry_config (BaseMCPRegistryConfig): The registry
                configuration to add.
        """
        self.registry_configs.append(registry_config)
        # Reinitialize the toolkit with the updated configurations
        self.mcp_toolkit = self._initialize_mcp_toolkit()

        # If already connected, reconnect to apply changes
        if self.mcp_toolkit and self.mcp_toolkit.is_connected:
            try:
                asyncio.run(self.disconnect())
                asyncio.run(self.connect())
            except RuntimeError as e:
                # Handle case where we're already in an event loop
                logger.warning(
                    f"Could not reconnect synchronously: {e}. "
                    f"Manual reconnection may be required."
                )

    @classmethod
    async def create(
        cls,
        config_path: Optional[str] = None,
        registry_configs: Optional[
            Union[List[BaseMCPRegistryConfig], BaseMCPRegistryConfig]
        ] = None,
        model: Optional[BaseModelBackend] = None,
        function_calling_available: bool = False,
        **kwargs,
    ) -> "MCPAgent":
        r"""Create and connect an MCPAgent instance.

        Args:
            config_path (Optional[str]): Path to the MCP configuration file.
                If provided, will load registry configs from this file.
                (default: :obj:`None`)
            registry_configs (Optional[Union[List[BaseMCPRegistryConfig],
                BaseMCPRegistryConfig]]): Registry configurations to use.
                Can be a single config or list of configs. If both config_path
                and registry_configs are provided, configs from both sources
                will be combined. (default: :obj:`None`)
            model (Optional[BaseModelBackend]): The model backend to use.
                If None, will use the default model. (default: :obj:`None`)
            function_calling_available (bool): Whether the model supports
                function calling. (default: :obj:`False`)
            **kwargs: Additional arguments to pass to MCPAgent constructor.

        Returns:
            MCPAgent: A connected MCPAgent instance ready to use.

        Example:
            >>> agent = await MCPAgent.create(
            ...     config_path="path/to/config.json",
            ...     function_calling_available=True
            ... )
            >>> response = await agent.run("Hello!")
        """
        # Initialize registry_configs list
        final_registry_configs = []

        # Add configs from registry_configs argument if provided
        if registry_configs is not None:
            if isinstance(registry_configs, BaseMCPRegistryConfig):
                final_registry_configs.append(registry_configs)
            else:
                final_registry_configs.extend(registry_configs)

        # Load additional configs from file if provided
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)

                # Create registry configs from the loaded data
                for _, server_config in config_data.get(
                    "mcpServers", {}
                ).items():
                    # Create a custom registry config for each server
                    registry_config = BaseMCPRegistryConfig(
                        type=MCPRegistryType.CUSTOM,
                        os=platform.system().lower(),  # type: ignore [arg-type]
                        **server_config,
                    )
                    final_registry_configs.append(registry_config)
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
                raise

        # Create the agent instance
        agent = cls(
            registry_configs=final_registry_configs,
            model=model,
            function_calling_available=function_calling_available,
            **kwargs,
        )

        # Connect to MCP servers
        try:
            await agent.connect()
        except Exception as e:
            logger.error(f"Failed to connect to MCP servers: {e}")
            await agent.disconnect()  # Clean up if connection fails
            raise

        return agent

    async def connect(self) -> None:
        r"""Connect to the MCP servers."""
        if self.mcp_toolkit:
            await self.mcp_toolkit.connect()
            if self.function_calling_available:
                self.add_tools(
                    cast(
                        list[FunctionTool | Callable[..., Any]],
                        self.mcp_toolkit.get_tools(),
                    )
                )
            else:
                prompt = TextPrompt(TOOLS_PROMPT)
                self._text_tools = prompt.format(
                    tools=self.mcp_toolkit.get_text_tools()
                )

    async def disconnect(self) -> None:
        r"""Disconnect from the MCP servers."""
        if self.mcp_toolkit:
            await self.mcp_toolkit.disconnect()

    async def astep(
        self, input_message: Union[BaseMessage, str], *args, **kwargs
    ) -> ChatAgentResponse:
        r"""Asynchronous step function. Make sure MCP toolkit is connected
        before proceeding.

        Args:
            input_message (Union[BaseMessage, str]): The input message.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            ChatAgentResponse: The response from the agent.
        """
        if self.mcp_toolkit and not self.mcp_toolkit.is_connected:
            await self.connect()

        if self.function_calling_available:
            return await super().astep(input_message, *args, **kwargs)
        else:
            task = f"## Task:\n  {input_message}"
            input_message = str(self._text_tools) + task
            response = await super().astep(input_message, *args, **kwargs)
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
                    try:
                        server_idx = tool_call.get('server_idx')
                        tool_name = tool_call.get('tool_name')
                        tool_args = tool_call.get('tool_args', {})

                        # Validate required fields
                        if server_idx is None or tool_name is None:
                            logger.warning(
                                f"Missing required fields in tool "
                                f"call: {tool_call}"
                            )
                            continue

                        # Check server index is valid
                        if (
                            not isinstance(server_idx, int)
                            or server_idx < 0
                            or server_idx >= len(self.mcp_toolkit.clients)
                        ):
                            logger.warning(
                                f"Invalid server index: {server_idx}"
                            )
                            continue

                        server = self.mcp_toolkit.clients[server_idx]
                        result = await server.call_tool(tool_name, tool_args)

                        # Safely access content
                        if result.content and len(result.content) > 0:
                            tools_results.append(
                                {tool_name: result.content[0].text}
                            )
                        else:
                            tools_results.append(
                                {tool_name: "No result content available"}
                            )
                    except Exception as e:
                        logger.error(f"Error processing tool call: {e}")
                        tools_results.append({"error": str(e)})
                results = json.dumps(tools_results)
                final_prompt = TextPrompt(FINAL_RESPONSE_PROMPT).format(
                    results=results
                )
                response = await self.astep(final_prompt)
                return response

    def step(
        self, input_message: Union[BaseMessage, str], *args, **kwargs
    ) -> ChatAgentResponse:
        r"""Synchronous step function. Make sure MCP toolkit is connected
        before proceeding.

        Args:
            input_message (Union[BaseMessage, str]): The input message.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            ChatAgentResponse: The response from the agent.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Running inside an existing loop (e.g., Jupyter/FastAPI)
            # Use create_task and run with a future
            coro = self.astep(input_message, *args, **kwargs)
            future = asyncio.ensure_future(coro)
            return asyncio.run_coroutine_threadsafe(future, loop).result()  # type: ignore [arg-type]
        else:
            # Safe to run normally
            return asyncio.run(self.astep(input_message, *args, **kwargs))

    async def __aenter__(self):
        r"""Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        r"""Async context manager exit."""
        await self.disconnect()
