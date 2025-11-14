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

from typing import List, Optional

from .mcp_toolkit import MCPToolkit


class PlaywrightMCPToolkit(MCPToolkit):
    r"""PlaywrightMCPToolkit provides an interface for interacting with web
    browsers using the Playwright automation library through the Model Context
    Protocol (MCP).

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
        additional_args (Optional[List[str]]): Additional command-line
            arguments to pass to the Playwright MCP server. For example,
            `["--cdp-endpoint=http://localhost:9222"]`.
            (default: :obj:`None`)

    Note:
        Currently only supports asynchronous operation mode.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        additional_args: Optional[List[str]] = None,
    ) -> None:
        r"""Initializes the PlaywrightMCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
            additional_args (Optional[List[str]]): Additional command-line
                arguments to pass to the Playwright MCP server. For example,
                `["--cdp-endpoint=http://localhost:9222"]`.
                (default: :obj:`None`)
        """
        # Create config for Playwright MCP server
        config_dict = {
            "mcpServers": {
                "playwright": {
                    "command": "npx",
                    "args": ["@playwright/mcp@latest"]
                    + (additional_args or []),
                }
            }
        }

        # Initialize parent MCPToolkit with Playwright configuration
        super().__init__(config_dict=config_dict, timeout=timeout)
