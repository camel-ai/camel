# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import os
from typing import Any, Dict, List, Optional

from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit


class GoogleCloudMCPToolkit(BaseToolkit):
    r"""GoogleCloudMCPToolkit provides Google Cloud Platform operations
    via MCP server, including BigQuery, Cloud Storage, Cloud Logging,
    and Compute Engine.

    Uses the ``google-cloud-mcp`` Python package. Requires a GCP
    service account JSON key file and project configuration.

    Example:
        async with GoogleCloudMCPToolkit(
            project_id="my-project",
            service_account_path="/path/to/sa.json",
        ) as toolkit:
            tools = toolkit.get_tools()

        # Or using environment variables
        async with GoogleCloudMCPToolkit() as toolkit:
            tools = toolkit.get_tools()

    Environment Variables:
        GCP_PROJECT_ID: Google Cloud project ID.
        GCP_SERVICE_ACCOUNT_PATH: Path to the service account JSON key.
        GCP_ALLOWED_BUCKETS: Comma-separated list of allowed GCS
            bucket names (optional).
        GCP_ALLOWED_DATASETS: Comma-separated list of allowed BigQuery
            datasets (optional).

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        service_account_path: Optional[str] = None,
        allowed_buckets: Optional[str] = None,
        allowed_datasets: Optional[str] = None,
        allowed_log_buckets: Optional[str] = None,
        allowed_instances: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the GoogleCloudMCPToolkit.

        Args:
            project_id (Optional[str]): GCP project ID. If None, reads
                from GCP_PROJECT_ID environment variable.
                (default: :obj:`None`)
            service_account_path (Optional[str]): Path to service account
                JSON key file. If None, reads from
                GCP_SERVICE_ACCOUNT_PATH environment variable.
                (default: :obj:`None`)
            allowed_buckets (Optional[str]): Comma-separated allowed GCS
                bucket names. (default: :obj:`None`)
            allowed_datasets (Optional[str]): Comma-separated allowed
                BigQuery dataset names. (default: :obj:`None`)
            allowed_log_buckets (Optional[str]): Comma-separated allowed
                log bucket names. (default: :obj:`None`)
            allowed_instances (Optional[str]): Comma-separated allowed
                Compute Engine instance names. (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        if project_id is None:
            project_id = os.getenv("GCP_PROJECT_ID")
        if service_account_path is None:
            service_account_path = os.getenv("GCP_SERVICE_ACCOUNT_PATH")

        if not project_id:
            raise ValueError(
                "project_id must be provided either as a parameter or "
                "through the GCP_PROJECT_ID environment variable"
            )
        if not service_account_path:
            raise ValueError(
                "service_account_path must be provided either as a "
                "parameter or through the GCP_SERVICE_ACCOUNT_PATH "
                "environment variable"
            )

        if allowed_buckets is None:
            allowed_buckets = os.getenv("GCP_ALLOWED_BUCKETS", "")
        if allowed_datasets is None:
            allowed_datasets = os.getenv("GCP_ALLOWED_DATASETS", "")
        if allowed_log_buckets is None:
            allowed_log_buckets = os.getenv("GCP_ALLOWED_LOG_BUCKETS", "")
        if allowed_instances is None:
            allowed_instances = os.getenv("GCP_ALLOWED_INSTANCES", "")

        args = [
            "google-cloud-mcp",
            "--project-id",
            project_id,
            "--service-account-path",
            service_account_path,
        ]
        if allowed_buckets:
            args.extend(["--allowed-buckets", allowed_buckets])
        if allowed_datasets:
            args.extend(["--allowed-datasets", allowed_datasets])
        if allowed_log_buckets:
            args.extend(["--allowed-log-buckets", allowed_log_buckets])
        if allowed_instances:
            args.extend(["--allowed-instances", allowed_instances])

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "google-cloud": {
                        "command": "uvx",
                        "args": args,
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the Google Cloud MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the Google Cloud MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server."""
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "GoogleCloudMCPToolkit":
        r"""Async context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the Google Cloud
        MCP server.

        Returns:
            List[FunctionTool]: List of available GCP tools.
        """
        return self._mcp_toolkit.get_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a Google Cloud tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
