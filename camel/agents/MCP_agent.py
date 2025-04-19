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
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union, cast

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool, MCPToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import track_agent

logger = get_logger(__name__)


class MCPRegistryType(Enum):
    """Enum for different types of MCP registries."""

    SMITHERY = auto()
    CUSTOM = auto()


class MCPRegistryConfig(BaseModel):
    """Configuration for an MCP registry.

    Attributes:
        name (str): The name of the registry.
        type (MCPRegistryType): The type of the registry.
        api_key (Optional[str]): API key for the registry.
    """

    type: MCPRegistryType
    api_key: Optional[str] = None

    def get_config(self) -> Dict:
        """Generate configuration based on registry type and API key.

        Returns:
            Dict: The complete configuration for the registry.
        """
        # Smithery
        if self.type == MCPRegistryType.SMITHERY:
            assert self.api_key is not None, "API key is required for Smithery"
            return {
                "toolbox": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@smithery/cli@latest",
                        "run",
                        "@smithery/toolbox",
                        "--config",
                        f'{{"dynamic":false,"smitheryApiKey":"{self.api_key}"}}',
                    ],
                }
            }
        return {}


@track_agent(name="MCPAgent")
class MCPAgent(ChatAgent):
    """A specialized agent designed to interact with MCP registries.
    The MCPAgent enhances a base ChatAgent by integrating MCP tools from
    various registries for search capabilities.

    Attributes:
        system_message (Optional[str]): The system message for the chat agent.
            (default: :str:`"You are an assistant with search capabilities
            using MCP tools."`)
        model (BaseModelBackend): The model backend to use for generating
            responses. (default: :obj:`ModelPlatformType.DEFAULT` with
            `ModelType.DEFAULT`)
        registry_configs (List[MCPRegistryConfig]): List of registry
            configurations (default: :obj:`None`)
        auto_connect (bool): Whether to automatically connect to MCP servers
            upon initialization. (default: :obj:`True`)
        **kwargs: Inherited from ChatAgent
    """

    def __init__(
        self,
        registry_configs: Union[List[MCPRegistryConfig], MCPRegistryConfig],
        system_message: Optional[str] = (
            "You are an assistant with search capabilities using MCP tools."
        ),
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        model: Optional[BaseModelBackend] = None,
        **kwargs,
    ):
        if model is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

        if isinstance(registry_configs, MCPRegistryConfig):
            self.registry_configs = [registry_configs]
        else:
            self.registry_configs = registry_configs or []

        # Initialize the toolkit if configuration is provided
        self.mcp_toolkit = self._initialize_mcp_toolkit()

        super().__init__(
            system_message=system_message,
            model=model,
            tools=tools,
            **kwargs,
        )

    def _initialize_mcp_toolkit(self) -> MCPToolkit:
        """Initialize the MCP toolkit from the provided configuration."""
        config_dict = {}
        for registry_config in self.registry_configs:
            config_dict.update(registry_config.get_config())

        # Wrap the config in a mcpServers key
        config_dict = {"mcpServers": config_dict}
        return MCPToolkit(config_dict=config_dict)

    async def connect(self) -> None:
        """Connect to the MCP servers."""
        if self.mcp_toolkit:
            await self.mcp_toolkit.connect()
            self.add_tools(
                cast(
                    list[FunctionTool | Callable[..., Any]],
                    self.mcp_toolkit.get_tools(),
                )
            )

    async def disconnect(self) -> None:
        """Disconnect from the MCP servers."""
        if self.mcp_toolkit:
            await self.mcp_toolkit.disconnect()

    async def astep(
        self, input_message: Union[BaseMessage, str], *args, **kwargs
    ) -> ChatAgentResponse:
        """Asynchronous step function.

        Make sure MCP toolkit is connected before proceeding.
        """
        if self.mcp_toolkit and not self.mcp_toolkit.is_connected():
            await self.connect()

        return await super().astep(input_message, *args, **kwargs)

    def step(
        self, input_message: Union[BaseMessage, str], *args, **kwargs
    ) -> ChatAgentResponse:
        """Synchronous step function.

        Make sure MCP toolkit is connected before proceeding.
        """
        if self.mcp_toolkit and not self.mcp_toolkit.is_connected():
            asyncio.run(self.connect())

        return super().step(input_message, *args, **kwargs)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
