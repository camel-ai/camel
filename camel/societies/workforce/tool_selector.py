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
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union

from camel.toolkits import ACIToolkit, MCPToolkit
from camel.types import (
    ACIRegistryConfig,
    BaseMCPRegistryConfig,
    SmitheryRegistryConfig,
)


class ToolSelector(ABC):
    r"""Abstract base class for all tool selectors.

    Subclasses must implement the [select_tools] method to provide
    different strategies for selecting tools based on task content.
    """

    @abstractmethod
    def select_tools(self, task_content: str) -> List[Any]:
        r"""Selects appropriate tools based on the given task content.

        Args:
            task_content (str): The description of the task that requires
            tools.

        Returns:
            List[Any]: A list of available tools.
        """
        pass


class RegistryToolSelector(ToolSelector):
    r"""Tool selector that supports multiple registry configurations for
    tool discovery and selection.

    This selector can work with different tool registries like ACI, Smithery,
    and others by using their respective registry configurations.
    """

    def __init__(
        self,
        registry_configs: Optional[
            Union[List[BaseMCPRegistryConfig], BaseMCPRegistryConfig]
        ] = None,
    ):
        r"""Initialize the registry tool selector.

        Args:
            registry_configs (Optional[Union[List[BaseMCPRegistryConfig],
                BaseMCPRegistryConfig]]): Registry configurations to use for
                tool discovery. Can be a single config or list of configs.
                (default: :obj:`None`)
        """
        if registry_configs is None:
            self.registry_configs = []
        elif isinstance(registry_configs, BaseMCPRegistryConfig):
            self.registry_configs = [registry_configs]
        else:
            self.registry_configs = registry_configs

    def add_registry(self, registry_config: BaseMCPRegistryConfig) -> None:
        r"""Add a new registry configuration.

        Args:
            registry_config (BaseMCPRegistryConfig): The registry
                configuration to add.
        """
        self.registry_configs.append(registry_config)

    def select_tools(self, task_content: str) -> List[Any]:
        r"""Selects tools from all configured registries based on task content.

        Args:
            task_content (str): Description of the task for tool discovery.

        Returns:
            List[Any]: A list of tools from all configured registries.
        """
        all_tools = []

        for registry_config in self.registry_configs:
            tools = self._get_tools_from_registry(
                registry_config, task_content
            )
            all_tools.extend(tools)

        return all_tools

    def _get_tools_from_registry(
        self, registry_config: BaseMCPRegistryConfig, task_content: str
    ) -> List[Any]:
        r"""Get tools from a specific registry configuration.

        Args:
            registry_config (BaseMCPRegistryConfig): The registry
                configuration.
            task_content (str): Description of the task for tool discovery.

        Returns:
            List[Any]: A list of tools from the specific registry.
        """
        from camel.types import MCPRegistryType

        if registry_config.type == MCPRegistryType.ACI:
            return self._get_aci_tools(
                registry_config,  # type: ignore[arg-type]
                task_content,
            )
        elif registry_config.type == MCPRegistryType.SMITHERY:
            return self._get_smithery_tools(
                registry_config,  # type: ignore[arg-type]
                task_content,
            )
        else:
            # For custom or other registry types, use MCPToolkit
            return self._get_mcp_tools(registry_config, task_content)

    def _get_aci_tools(
        self, registry_config: ACIRegistryConfig, task_content: str
    ) -> List[Any]:
        r"""Get tools from ACI registry.

        Args:
            registry_config (ACIRegistryConfig): ACI registry configuration.
            task_content (str): Description of the task for tool discovery.

        Returns:
            List[Any]: A list of ACI tools.
        """
        aci_toolkit = ACIToolkit(
            api_key=registry_config.api_key,
            linked_account_owner_id=registry_config.linked_account_owner_id,
        )
        return aci_toolkit.get_tools()

    def _get_smithery_tools(
        self, registry_config: SmitheryRegistryConfig, task_content: str
    ) -> List[Any]:
        r"""Get tools from Smithery registry using MCP.

        Args:
            registry_config (SmitheryRegistryConfig): Smithery registry
                configuration.
            task_content (str): Description of the task for tool discovery.

        Returns:
            List[Any]: A list of Smithery tools.
        """
        # Use MCPToolkit with Smithery configuration
        config_dict = registry_config.get_config()
        mcp_toolkit = MCPToolkit(config_dict=config_dict)
        return mcp_toolkit.get_tools()

    def _get_mcp_tools(
        self, registry_config: BaseMCPRegistryConfig, task_content: str
    ) -> List[Any]:
        r"""Get tools from generic MCP registry.

        Args:
            registry_config (BaseMCPRegistryConfig): MCP registry
                configuration.
            task_content (str): Description of the task for tool discovery.

        Returns:
            List[Any]: A list of MCP tools.
        """
        config_dict = registry_config.get_config()
        mcp_toolkit = MCPToolkit(config_dict=config_dict)
        return mcp_toolkit.get_tools()
