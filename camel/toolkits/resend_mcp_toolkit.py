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

from camel.toolkits import FunctionTool

from .mcp_toolkit import MCPToolkit


class ResendMCPToolkit(MCPToolkit):
    r"""ResendMCPToolkit provides an interface for sending emails using 
    Resend's API through the Model Context Protocol (MCP).

    This toolkit inherits from MCPToolkit and configures it specifically
    for the Resend email service. It enables sending plain text and HTML 
    emails, scheduling emails for future delivery, adding CC and BCC 
    recipients, configuring reply-to addresses, and listing Resend audiences.

    The toolkit automatically manages the connection to the Resend MCP server
    and provides all the standard MCPToolkit functionality like connect(),
    disconnect(), get_tools(), and async context manager support.

    Args:
        api_key (str): Resend API key for authentication. Required for all
            email operations.
        mcp_server_path (str): Path to the built Resend MCP server 
            (build/index.js). This should be the absolute path to the
            built JavaScript file from the mcp-send-email project.
        sender_email (Optional[str]): Default sender email address from a 
            verified domain. If not provided, must be specified for each 
            email send operation. (default: :obj:`None`)
        reply_to_email (Optional[str]): Default reply-to email address. 
            (default: :obj:`None`)
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)

    Note:
        - To send emails to external addresses, you need to verify your domain 
          with Resend.
        - Requires the mcp-send-email project to be cloned and built locally:
          git clone https://github.com/resend/mcp-send-email.git
          cd mcp-send-email && npm install && npm run build
        - Supports both manual connection management and async context manager.

    Example:
        .. code-block:: python

            # Using async context manager (recommended)
            async with ResendMCPToolkit(
                api_key="your_key",
                mcp_server_path="/path/to/mcp-send-email/build/index.js"
            ) as toolkit:
                tools = toolkit.get_tools()
                # Use email tools...

            # Manual connection management
            toolkit = ResendMCPToolkit(
                api_key="your_key",
                mcp_server_path="/path/to/mcp-send-email/build/index.js"
            )
            await toolkit.connect()
            try:
                tools = toolkit.get_tools()
                # Use email tools...
            finally:
                await toolkit.disconnect()
    """

    def __init__(
        self,
        api_key: str,
        mcp_server_path: str,
        sender_email: Optional[str] = None,
        reply_to_email: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the ResendMCPToolkit.

        Args:
            api_key (str): Resend API key for authentication. You can get this
                from your Resend dashboard.
            mcp_server_path (str): Path to the built Resend MCP server 
                (build/index.js). This should be the absolute path to the
                built JavaScript file from the mcp-send-email project.
            sender_email (Optional[str]): Default sender email address from a
                verified domain. If not provided, must be specified for each
                email send operation. (default: :obj:`None`)
            reply_to_email (Optional[str]): Default reply-to email address.
                (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)

        Raises:
            ValueError: If api_key or mcp_server_path is not provided or is empty.
        """
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required and cannot be empty")
            
        if not mcp_server_path or not mcp_server_path.strip():
            raise ValueError("mcp_server_path is required and cannot be empty")

        # Prepare command arguments for the Resend MCP server
        args = ["--key", api_key]
        
        if sender_email:
            args.extend(["--sender", sender_email])
            
        if reply_to_email:
            args.extend(["--reply-to", reply_to_email])

        # Initialize parent MCPToolkit with Resend server configuration
        super().__init__(
            config_dict={
                "mcpServers": {
                    "resend": {
                        "command": "node",
                        "args": [mcp_server_path] + args,
                    }
                }
            },
            timeout=timeout,
        )
