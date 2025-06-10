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
import os
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.prompts import TextPrompt
from camel.societies.workforce.tool_selector import (
    RegistryToolSelector,
    ToolSelector,
)
from camel.types import (
    ACIRegistryConfig,
    BaseMCPRegistryConfig,
    ModelPlatformType,
    ModelType,
    SmitheryRegistryConfig,
)


class DynamicAgentCreator:
    r"""A class to dynamically create agents based on task content.
    Supports multiple tool discovery strategies and registry configurations.

    Attributes:
        tool_selector (ToolSelector): An instance of ToolSelector used for
            selecting tools based on the task.
        model (Optional[BaseModelBackend]): The default model backend to use
            for agent creation. If None, will use default model settings.
    """

    def __init__(
        self,
        tool_selector: ToolSelector,
        model: Optional[BaseModelBackend] = None,
    ):
        r"""Initializes the DynamicAgentCreator with a tool selector and
        optional model.

        Args:
            tool_selector (ToolSelector): The tool selector instance to be used
                for tool discovery.
            model (Optional[BaseModelBackend]): The model backend to use for
                agent creation. If None, will use default model settings.
        """
        self.tool_selector = tool_selector
        self.model = model

    @classmethod
    def create_with_registries(
        cls,
        registry_configs: Optional[
            Union[List[BaseMCPRegistryConfig], BaseMCPRegistryConfig]
        ] = None,
        model: Optional[BaseModelBackend] = None,
    ) -> "DynamicAgentCreator":
        r"""Create a DynamicAgentCreator with registry-based tool selection.

        Args:
            registry_configs (Optional[Union[List[BaseMCPRegistryConfig],
                BaseMCPRegistryConfig]]): Registry configurations for tool
                discovery. If None, will attempt to create default
                configurations from environment variables.
            model (Optional[BaseModelBackend]): The model backend to use for
                agent creation. If None, will use default model settings.

        Returns:
            DynamicAgentCreator: Instance with RegistryToolSelector configured.
        """
        if registry_configs is None:
            registry_configs = cls._create_default_registries()

        tool_selector = RegistryToolSelector(registry_configs=registry_configs)
        return cls(tool_selector, model=model)

    @classmethod
    def create_with_aci(
        cls,
        api_key: Optional[str] = None,
        linked_account_owner_id: Optional[str] = None,
        os_type: Literal["darwin", "linux", "windows"] = "darwin",
        model: Optional[BaseModelBackend] = None,
    ) -> "DynamicAgentCreator":
        r"""Create a DynamicAgentCreator with ACI registry configuration.

        Args:
            api_key (Optional[str]): ACI API key. If None, will use
                ACI_API_KEY environment variable.
            linked_account_owner_id (Optional[str]): ACI linked account owner
                ID. If None, will use ACI_LINKED_ACCOUNT_OWNER_ID environment
                variable.
            os_type (Literal["darwin", "linux", "windows"]): Operating system
                type. Default is "darwin".
            model (Optional[BaseModelBackend]): The model backend to use for
                agent creation. If None, will use default model settings.

        Returns:
            DynamicAgentCreator: Instance configured for ACI tool discovery.
        """
        api_key_val = api_key or os.getenv("ACI_API_KEY")
        owner_id_val = linked_account_owner_id or os.getenv(
            "ACI_LINKED_ACCOUNT_OWNER_ID"
        )

        if not api_key_val or not owner_id_val:
            raise ValueError(
                "ACI_API_KEY and ACI_LINKED_ACCOUNT_OWNER_ID must be provided"
            )

        aci_config = ACIRegistryConfig(
            api_key=api_key_val,
            linked_account_owner_id=owner_id_val,
            os=os_type,
        )
        return cls.create_with_registries([aci_config], model=model)

    @classmethod
    def create_with_smithery(
        cls,
        api_key: Optional[str] = None,
        profile: Optional[str] = None,
        os_type: Literal["darwin", "linux", "windows"] = "darwin",
        model: Optional[BaseModelBackend] = None,
    ) -> "DynamicAgentCreator":
        r"""Create a DynamicAgentCreator with Smithery registry configuration.

        Args:
            api_key (Optional[str]): Smithery API key. If None, will use
                SMITHERY_API_KEY environment variable.
            profile (Optional[str]): Smithery profile. If None, will use
                SMITHERY_PROFILE environment variable or "default".
            os_type (Literal["darwin", "linux", "windows"]): Operating system
                type. Default is "darwin".
            model (Optional[BaseModelBackend]): The model backend to use for
                agent creation. If None, will use default model settings.

        Returns:
            DynamicAgentCreator: Instance configured for Smithery tool
                discovery.
        """
        api_key_val = api_key or os.getenv("SMITHERY_API_KEY")
        profile_val = profile or os.getenv("SMITHERY_PROFILE", "default")

        if not api_key_val:
            raise ValueError("SMITHERY_API_KEY must be provided")

        smithery_config = SmitheryRegistryConfig(
            api_key=api_key_val,
            profile=profile_val or "default",
            os=os_type,
        )
        return cls.create_with_registries([smithery_config], model=model)

    @classmethod
    def create_with_legacy_aci(
        cls,
        linked_account_owner_id: Optional[str] = None,
        model: Optional[BaseModelBackend] = None,
    ) -> "DynamicAgentCreator":
        r"""Create a DynamicAgentCreator with legacy ACI tool selector.

        Args:
            linked_account_owner_id (Optional[str]): ACI linked account owner
                ID. If None, will use ACI_LINKED_ACCOUNT_OWNER_ID environment
                variable.
            model (Optional[BaseModelBackend]): The model backend to use for
                agent creation. If None, will use default model settings.

        Returns:
            DynamicAgentCreator: Instance with legacy tool selector.

        Note:
            This method is provided for backward compatibility. Consider using
                create_with_aci() for new implementations.
        """
        # For backward compatibility, create an ACI registry config
        owner_id_val = linked_account_owner_id or os.getenv(
            "ACI_LINKED_ACCOUNT_OWNER_ID"
        )
        api_key_val = os.getenv("ACI_API_KEY")

        if not api_key_val or not owner_id_val:
            raise ValueError(
                "ACI_API_KEY and ACI_LINKED_ACCOUNT_OWNER_ID must be provided"
            )

        aci_config = ACIRegistryConfig(
            api_key=api_key_val,
            linked_account_owner_id=owner_id_val,
            os="darwin",  # type: ignore[arg-type]
        )
        tool_selector = RegistryToolSelector(registry_configs=[aci_config])
        return cls(tool_selector, model=model)

    @staticmethod
    def _create_default_registries() -> List[BaseMCPRegistryConfig]:
        r"""Create default registry configurations from environment variables.

        Returns:
            List[BaseMCPRegistryConfig]: List of available registry
                configurations based on environment variables.
        """
        registries: List[BaseMCPRegistryConfig] = []

        # Default OS type - can be made configurable if needed
        default_os: Literal["darwin", "linux", "windows"] = "darwin"

        # Add ACI registry if configured
        if os.getenv("ACI_API_KEY") and os.getenv(
            "ACI_LINKED_ACCOUNT_OWNER_ID"
        ):
            aci_config = ACIRegistryConfig(
                api_key=os.getenv("ACI_API_KEY"),  # type: ignore[arg-type]
                linked_account_owner_id=os.getenv(
                    "ACI_LINKED_ACCOUNT_OWNER_ID"
                ),  # type: ignore[arg-type]
                os=default_os,
            )
            registries.append(aci_config)

        # Add Smithery registry if configured
        if os.getenv("SMITHERY_API_KEY"):
            smithery_config = SmitheryRegistryConfig(
                api_key=os.getenv("SMITHERY_API_KEY"),  # type: ignore[arg-type]
                profile=os.getenv("SMITHERY_PROFILE") or "default",
                os=default_os,
            )
            registries.append(smithery_config)

        return registries

    def add_registry(self, registry_config: BaseMCPRegistryConfig) -> None:
        r"""Add a new registry configuration to the tool selector.

        Args:
            registry_config (BaseMCPRegistryConfig): The registry
                configuration to add.

        Raises:
            AttributeError: If the tool selector doesn't support adding
                registries (e.g., legacy selectors).
        """
        if hasattr(self.tool_selector, 'add_registry'):
            self.tool_selector.add_registry(registry_config)
        else:
            raise AttributeError(
                f"Tool selector of type {type(self.tool_selector)} does not "
                f"support adding registries. Consider "
                f"using RegistryToolSelector."
            )

    class PromptModel(BaseModel):
        role: str = Field(description="The role of the assistant.")
        sys_msg: str = Field(
            description="The system message for the assistant."
        )

    def generate_prompt(self, task_content: str) -> PromptModel:
        r"""Generates a JSON-formatted prompt containing a role name and system
        message for an agent, based on the provided task content using an LLM.

        Args:
            task_content (str): Description of the task for which the agent is
                being created.

        Returns:
            PromptModel: A model containing 'role' and 'sys_msg' representing
                the agent's role and system message.
        """
        prompt = TextPrompt(
            """Given the following task, create an optimized role and system
                message for the agent:

            Task: {task_content}
            
            The role should be concise and descriptive of the agent's function.
            The system message should provide clear instructions for how the 
            agent should behave and what it should focus on when handling 
            similar tasks.
            """
        ).format(task_content=task_content)

        model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        agent = ChatAgent(system_message=prompt, model=model)

        response = agent.step(task_content, response_format=self.PromptModel)
        content_str = response.msgs[0].content
        content_dict = json.loads(content_str)
        return self.PromptModel(**content_dict)

    def select_tools(self, task_content: str) -> list:
        r"""Uses the tool selector to find relevant tools for the given task
        content.

        Args:
            task_content (str): Description of the task for which tools are
                being selected.

        Returns:
            list: A list of selected tools suitable for handling the task.
        """
        return self.tool_selector.select_tools(task_content)

    def get_registry_info(self) -> dict:
        r"""Get information about configured registries.

        Returns:
            dict: Information about the tool selector and its configurations.
        """
        info = {
            "tool_selector_type": type(self.tool_selector).__name__,
            "supports_multiple_registries": hasattr(
                self.tool_selector, 'registry_configs'
            ),
        }

        if hasattr(self.tool_selector, 'registry_configs'):
            info["configured_registries"] = [
                {
                    "type": config.type.name,
                    "has_api_key": config.api_key is not None,
                }
                for config in self.tool_selector.registry_configs
            ]

        return info

    def create_agent(self, task_content: str) -> ChatAgent:
        r"""Orchestrates the agent creation process by:
        1. Generating a system prompt using the task content.
        2. Selecting appropriate tools from configured registries.
        3. Configuring a model with the selected tools.
        4. Creating and returning a ChatAgent instance.

        Args:
            task_content (str): Description of the task for which the agent is
                being created.

        Returns:
            ChatAgent: A fully configured agent ready to execute the task.
        """
        # Step 1: Generate system prompt
        prompt_info = self.generate_prompt(task_content)

        # Step 2: Discover tools using the configured tool selector
        tools = self.select_tools(task_content)

        # Step 3: Build model configuration
        if self.model is not None:
            # Use the provided model
            model = self.model
        else:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

        # Step 4: Create Agent
        sys_msg = BaseMessage.make_assistant_message(
            role_name=prompt_info.role, content=prompt_info.sys_msg
        )
        agent = ChatAgent(sys_msg, model=model, tools=tools)

        return agent
