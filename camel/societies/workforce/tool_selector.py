# =====================
# Tool Selector Interface
# =====================
import os
from abc import ABC, abstractmethod
from typing import Any, List

from camel.agents import MCPAgent
from camel.models import ModelFactory
from camel.types import (
    ACIRegistryConfig,
    BaseMCPRegistryConfig,
    ModelPlatformType,
    ModelType,
)


class ToolSelector(ABC):
    """
    Abstract base class for all tool selectors.

    Subclasses must implement the [select_tools] method to provide
    different strategies for selecting tools based on task content.
    """

    @abstractmethod
    def select_tools(self, task_content: str) -> List[Any]:
        """
        Selects appropriate tools based on the given task content.

        Args:
            task_content (str): The description of the task that requires
            tools.

        Returns:
            List[Any]: A list of available tools.
        """
        pass


class ACIMCPToolSelector(ToolSelector):
    """
    Tool selector using ACI Registry and MCPAgent to dynamically discover
    tools.

    This class connects to the ACI MCP registry and uses an `MCPAgent` instance
    to search for relevant tools based on the provided task content.
    """

    def __init__(self, aci_config: BaseMCPRegistryConfig = None):
        """
        Initializes the ACIMCPToolSelector with an optional ACI registry
        config.

        If no configuration is provided, it will use environment variables:
        - `ACI_API_KEY`
        - `ACI_LINKED_ACCOUNT_OWNER_ID`

        Args:
            aci_config (BaseMCPRegistryConfig, optional): Configuration for the
            ACI registry.
                If not provided, a default ACIRegistryConfig will be used.
                Defaults to None.
        """
        self.aci_config = aci_config or ACIRegistryConfig(
            api_key=os.getenv("ACI_API_KEY"),
            linked_account_owner_id=os.getenv("ACI_LINKED_ACCOUNT_OWNER_ID"),
        )
        self.mcp_agent = None

    async def _initialize_mcp_agent(self):
        """Initializes the MCPAgent with default model and registry
        configuration."""
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        self.mcp_agent = await MCPAgent.create(
            registry_configs=[self.aci_config],
            model=model,
            function_calling_available=False,
        )

    def select_tools(self, task_content: str) -> list:
        """
        Searches for tools related to the given task content using the ACI
        registry.

        If the MCP agent has not been initialized yet, it will be created
        before performing the search.

        Args:
            task_content (str): The task description used for searching tools.

        Returns:
            List[Any]: A list of function tools found via ACI MCP registry.

        Raises:
            Exception: If there's a failure during MCP tool search.
        """
