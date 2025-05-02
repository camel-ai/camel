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
from typing import Any, Dict, List, Optional

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required, dependencies_required


@MCPServer()
class KlavisToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with Klavis API.

    This class provides methods for interacting with Klavis MCP server
    instances, retrieving server information, managing tools, and handling
    authentication.

    Attributes:
        api_key (str): The API key for authenticating with Klavis API.
        base_url (str): The base URL for Klavis API endpoints.
        timeout (Optional[float]): The timeout value for API requests
            in seconds. If None, no timeout is applied.
            (default: :obj:`None`)
    """

    @dependencies_required("requests")
    @api_keys_required(
        [
            (None, "KLAVIS_API_KEY"),
        ]
    )
    def __init__(self, timeout: Optional[float] = None) -> None:
        super().__init__(timeout=timeout)
        r"""Initialize the KlavisToolkit with API client. The API key is
        retrieved from environment variables.
        """
        self.api_key = os.environ.get("KLAVIS_API_KEY")
        self.base_url = "https://api.klavis.ai"

    def create_server_instance(
        self, server_name: str, user_id: str, platform_name: str
    ) -> Dict[str, Any]:
        r"""Create a Server-Sent Events (SSE) URL for a specified MCP server.

        Args:
            server_name (str): The name of the target MCP server.
            user_id (str): The ID for the user requesting the server URL.
            platform_name (str): The name of the platform associated
              with the user.

        Returns:
            Dict[str, Any]: Response containing the server instance details.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            payload = {
                "serverName": server_name,
                "userId": user_id,
                "platformName": platform_name,
            }
            response = requests.post(
                f"{self.base_url}/mcp-server/instance/create",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def get_server_instance(self, instance_id: str) -> Dict[str, Any]:
        r"""Get details of a specific server connection instance.

        Args:
            instance_id (str): The ID of the connection instance whose status
                is being checked.

        Returns:
            Dict[str, Any]: Details about the server instance.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.get(
                f"{self.base_url}/mcp-server/instance/get/{instance_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def delete_auth_data(self, instance_id: str) -> Dict[str, Any]:
        r"""Delete authentication metadata for a specific server
        connection instance.

        Args:
            instance_id (str): The ID of the connection instance to
              delete auth for.

        Returns:
            Dict[str, Any]: Status response for the operation.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.delete(
                f"{self.base_url}/mcp-server/instance/delete-auth/{instance_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def delete_server_instance(self, instance_id: str) -> Dict[str, Any]:
        r"""Completely removes a server connection instance.

        Args:
            instance_id (str): The ID of the connection instance to delete.

        Returns:
            Dict[str, Any]: Status response for the operation.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.delete(
                f"{self.base_url}/mcp-server/instance/delete/{instance_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def get_server_tools(self, server_name: str) -> Dict[str, Any]:
        r"""Get list of tool names for a specific MCP server.

        Args:
            server_name (str): The name of the target MCP server.

        Returns:
            Dict[str, Any]: List of tools available for the specified server.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.get(
                f"{self.base_url}/mcp-server/tools/{server_name}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def get_all_servers(self) -> Dict[str, Any]:
        r"""Get all MCP servers with their basic information.

        Returns:
            Dict[str, Any]: Information about all available MCP servers.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.get(
                f"{self.base_url}/mcp-server/servers",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def set_auth_token(
        self, instance_id: str, auth_token: str
    ) -> Dict[str, Any]:
        r"""Sets an authentication token for a specific instance.

        Args:
            instance_id (str): The ID for the connection instance.
            auth_token (str): The authentication token to save.

        Returns:
            Dict[str, Any]: Status response for the operation.
        """
        try:
            headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            payload = {"instanceId": instance_id, "authToken": auth_token}
            response = requests.post(
                f"{self.base_url}/mcp-server/instance/set-auth-token",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.create_server_instance),
            FunctionTool(self.get_server_instance),
            FunctionTool(self.delete_auth_data),
            FunctionTool(self.delete_server_instance),
            FunctionTool(self.get_server_tools),
            FunctionTool(self.get_all_servers),
            FunctionTool(self.set_auth_token),
        ]
