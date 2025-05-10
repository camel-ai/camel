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
import os
import platform
from enum import Enum, auto
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class MCPRegistryType(Enum):
    r"""Enum for different types of MCP registries."""

    SMITHERY = auto()
    ACI = auto()
    CUSTOM = auto()


class BaseMCPRegistryConfig(BaseModel):
    r"""Base configuration for an MCP registry.

    Attributes:
        type (MCPRegistryType): The type of the registry.
        os (Literal["darwin", "linux", "windows"]): The operating system. It
            is automatically set to "darwin" for MacOS, "linux" for Linux, and
            "windows" for Windows.
        api_key (Optional[str]): API key for the registry.
    """

    type: MCPRegistryType
    os: Literal["darwin", "linux", "windows"]
    api_key: Optional[str] = None

    def get_config(self) -> Dict[str, Any]:
        r"""Generate configuration based on registry type and API key.

        Returns:
            Dict[str, Any]: The complete configuration for the registry.
        """
        return {}

    @model_validator(mode='before')
    @classmethod
    def set_default_os(cls, values: Dict) -> Dict:
        r"""Set the default OS based on the current platform if not provided.

        Args:
            values (Dict): The values dictionary from the model validation.

        Returns:
            Dict: The updated values dictionary with the OS set.

        Raises:
            ValueError: If the current system is not supported.
        """
        if 'os' not in values or values['os'] is None:
            system = platform.system().lower()
            if system in ('darwin', 'linux', 'windows'):
                values['os'] = system
            else:
                raise ValueError(f"Unsupported system: {system}")
        return values

    def _prepare_command_args(
        self, command: str, args: List[str]
    ) -> Dict[str, Any]:
        r"""Prepare command and arguments based on OS.

        Args:
            command (str): The base command to run.
            args (List[str]): The arguments for the command.

        Returns:
            Dict[str, Any]: Command configuration with OS-specific adjustments.
        """
        if self.os == "windows":
            return {"command": "cmd", "args": ["/c", command, *args]}
        else:  # darwin or linux
            return {"command": command, "args": args}


class SmitheryRegistryConfig(BaseMCPRegistryConfig):
    r"""Configuration for Smithery registry."""

    type: MCPRegistryType = MCPRegistryType.SMITHERY
    profile: str = Field(
        ..., description="The profile to use for the registry."
    )

    def get_config(self) -> Dict[str, Any]:
        r"""Generate configuration for Smithery registry.

        Returns:
            Dict[str, Any]: The complete configuration for the registry.
        """
        api_key = self.api_key or os.environ.get("SMITHERY_API_KEY")

        args = [
            "-y",
            "@smithery/cli@latest",
            "run",
            "@smithery/toolbox",
            "--key",
            api_key,
            "--profile",
            self.profile,
        ]

        cmd_config = self._prepare_command_args("npx", args)  # type: ignore[arg-type]

        return {"mcpServers": {"toolbox": cmd_config}}


class ACIRegistryConfig(BaseMCPRegistryConfig):
    r"""Configuration for ACI registry."""

    type: MCPRegistryType = MCPRegistryType.ACI
    linked_account_owner_id: str = Field(
        ..., description="The owner ID of the linked account."
    )

    def get_config(self) -> Dict[str, Any]:
        r"""Generate configuration for ACI registry.

        Returns:
            Dict[str, Any]: The complete configuration for the registry.
        """
        api_key = self.api_key or os.environ.get("ACI_API_KEY")

        args = [
            "aci-mcp",
            "unified-server",
            "--linked-account-owner-id",
            self.linked_account_owner_id,
        ]

        cmd_config = self._prepare_command_args("uvx", args)

        return {
            "mcpServers": {
                "aci-mcp-unified": {
                    **cmd_config,
                    "env": {"ACI_API_KEY": api_key},
                }
            }
        }
