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

from typing import Optional

from .mcp_toolkit import MCPToolkit


class GoogleDriveMCPToolkit(MCPToolkit):
    r"""GoogleDriveMCPToolkit provides an interface for interacting with
    Google Drive using the Google Drive MCP server.

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        credentials_path: Optional[str] = None,
    ) -> None:
        r"""Initializes the GoogleDriveMCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
            credentials_path (Optional[str]): Path to the Google Drive
                credentials file. (default: :obj:`None`)
        """

        config_dict = {
            "mcpServers": {
                "gdrive": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-gdrive"],
                    "env": {"GDRIVE_CREDENTIALS_PATH": credentials_path},
                }
            }
        }

        # Initialize parent MCPToolkit with Playwright configuration
        super().__init__(config_dict=config_dict, timeout=timeout)
