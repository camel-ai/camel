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
import urllib.parse
from typing import Any, Dict, List, Optional

import requests

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import (
    MCPServer,
    api_keys_required,
    dependencies_required,
)

logger = get_logger(__name__)


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
        r"""Initialize the KlavisToolkit with API client. The API key is
        retrieved from environment variables.
        """
        super().__init__(timeout=timeout)
        self.api_key = os.environ.get("KLAVIS_API_KEY")
        self.base_url = "https://api.klavis.ai"

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        r"""Make an HTTP request to the Klavis API.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST', 'DELETE').
            endpoint (str): API endpoint path.
            payload (Optional[Dict[str, Any]]): JSON payload for POST
                requests.
            additional_headers (Optional[Dict[str, str]]): Additional
                headers to include in the request.

        Returns:
            Dict[str, Any]: The JSON response from the API or an error
                dict.
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        if additional_headers:
            headers.update(additional_headers)

        logger.debug(
            f"Making {method} request to {url} with payload: {payload}"
        )

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {method} {endpoint}: {e!s}")
            return {"error": f"Request failed: {e!s}"}
        except ValueError:
            logger.error(f"Response for {method} {endpoint} is not valid JSON")
            return {"error": "Response is not valid JSON"}

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
        endpoint = "/mcp-server/instance/create"
        payload = {
            "serverName": server_name,
            "userId": user_id,
            "platformName": platform_name,
        }
        headers = {'Content-Type': 'application/json'}
        return self._request(
            'POST', endpoint, payload=payload, additional_headers=headers
        )

    def get_server_instance(self, instance_id: str) -> Dict[str, Any]:
        r"""Get details of a specific server connection instance.

        Args:
            instance_id (str): The ID of the connection instance whose status
                is being checked.

        Returns:
            Dict[str, Any]: Details about the server instance.
        """
        endpoint = f"/mcp-server/instance/get/{instance_id}"
        return self._request('GET', endpoint)

    def delete_auth_data(self, instance_id: str) -> Dict[str, Any]:
        r"""Delete authentication metadata for a specific server
        connection instance.

        Args:
            instance_id (str): The ID of the connection instance to
              delete auth for.

        Returns:
            Dict[str, Any]: Status response for the operation.
        """
        endpoint = f"/mcp-server/instance/delete-auth/{instance_id}"
        return self._request('DELETE', endpoint)

    def delete_server_instance(self, instance_id: str) -> Dict[str, Any]:
        r"""Completely removes a server connection instance.

        Args:
            instance_id (str): The ID of the connection instance to delete.

        Returns:
            Dict[str, Any]: Status response for the operation.
        """
        endpoint = f"/mcp-server/instance/delete/{instance_id}"
        return self._request('DELETE', endpoint)

    def get_all_servers(self) -> Dict[str, Any]:
        r"""Get all MCP servers with their basic information.

        Returns:
            Dict[str, Any]: Information about all available MCP servers.
        """
        endpoint = "/mcp-server/servers"
        return self._request('GET', endpoint)

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
        endpoint = "/mcp-server/instance/set-auth-token"
        payload = {"instanceId": instance_id, "authToken": auth_token}
        headers = {'Content-Type': 'application/json'}
        return self._request(
            'POST', endpoint, payload=payload, additional_headers=headers
        )

    def list_tools(self, server_url: str) -> Dict[str, Any]:
        r"""Lists all tools available for a specific remote MCP server.

        Args:
            server_url (str): The full URL for connecting to the MCP server
                via Server-Sent Events (SSE).

        Returns:
            Dict[str, Any]: Response containing the list of tools or an error.
        """

        encoded_server_url = urllib.parse.quote(server_url, safe='')
        endpoint = f"/mcp-server/list-tools/{encoded_server_url}"
        return self._request('GET', endpoint)

    def call_tool(
        self,
        server_url: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r"""Calls a remote MCP server tool directly using the provided server
        URL.

        Args:
            server_url (str): The full URL for connecting to the MCP server
                via Server-Sent Events (SSE).
            tool_name (str): The name of the tool to call.
            tool_args (Optional[Dict[str, Any]]): The input parameters for
                the tool. Defaults to None, which might be treated as empty
                args by the server. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Response containing the result of the tool call
                or an error.
        """
        endpoint = "/mcp-server/call-tool"
        payload: Dict[str, Any] = {
            "serverUrl": server_url,
            "toolName": tool_name,
        }
        # Add toolArgs only if provided, otherwise server might expect empty
        # dict
        if tool_args is not None:
            payload["toolArgs"] = tool_args
        else:
            # Explicitly setting to empty dict based on schema interpretation
            payload["toolArgs"] = {}

        headers = {'Content-Type': 'application/json'}
        return self._request(
            'POST', endpoint, payload=payload, additional_headers=headers
        )

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
            FunctionTool(self.get_all_servers),
            FunctionTool(self.set_auth_token),
            FunctionTool(self.list_tools),
            FunctionTool(self.call_tool),
        ]
