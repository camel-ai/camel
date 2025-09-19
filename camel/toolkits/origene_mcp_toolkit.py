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

from typing import Dict, Optional

from .mcp_toolkit import MCPToolkit


class OrigeneToolkit(MCPToolkit):
    r"""OrigeneToolkit provides an interface for interacting with
    Origene MCP server.

    This toolkit can be used as an async context manager for automatic
    connection management:

        async with OrigeneToolkit(config_dict=config) as toolkit:
            tools = toolkit.get_tools()
            # Toolkit is automatically disconnected when exiting

    Attributes:
        config_dict (Dict): Configuration dictionary for MCP servers.
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        config_dict: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the OrigeneToolkit.

        Args:
            config_dict (Optional[Dict]): Configuration dictionary for MCP
                servers. If None, raises ValueError as configuration is
                required. (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        # Validate that config_dict is provided
        if config_dict is None:
            raise ValueError("config_dict must be provided")

        # Initialize parent MCPToolkit with provided configuration
        super().__init__(config_dict=config_dict, timeout=timeout)
