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

from typing import Any

from .mcp_toolkit import MCPToolkit


class AtomicMailToolkit(MCPToolkit):
    r"""AtomicMailToolkit gives an agent an email inbox of its own through
    the Atomic Mail MCP server.

    Unlike the Gmail and IMAP toolkits, which connect the agent to a mailbox
    a person already owns, this toolkit lets the agent provision its own
    address: the ``register`` tool solves a proof-of-work challenge and
    returns an ``@atomicmail.ai`` inbox with no signup, domain or card. The
    agent then sends, reads and searches over JMAP (RFC 8620/8621).

    Three tools are exposed by the server:

    - ``register``: proof-of-work signup that provisions an inbox and stores
      its credentials. Takes a username of 5-21 characters and a ``watch``
      value of ``scheduled`` or ``on-demand``.
    - ``jmap_request``: runs a JMAP method-call batch, authenticated
      automatically. Takes inline ``ops`` or a named preset such as
      ``list_inbox.json``, ``send_mail.json`` or ``reply.json``.
    - ``help``: serves the bundled docs, including the preset list and a JMAP
      cheatsheet.

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)

    Note:
        Running the local server requires Node.js, since it is started with
        ``npx``. Set :obj:`api_key` only to reuse an inbox that already
        exists; leave it unset and let the agent call ``register``.
    """

    def __init__(
        self,
        timeout: float | None = None,
        api_key: str | None = None,
        credentials_dir: str | None = None,
    ) -> None:
        r"""Initializes the AtomicMailToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
            api_key (Optional[str]): API key for an existing Atomic Mail
                inbox. Omit it to let the agent register a new one.
                (default: :obj:`None`)
            credentials_dir (Optional[str]): Directory the inbox credentials
                are read from and written to. Pass a separate directory per
                toolkit instance to drive more than one inbox from the same
                process. (default: :obj:`None`)
        """
        env: dict[str, str] = {}
        if api_key is not None:
            env["ATOMIC_MAIL_API_KEY"] = api_key
        if credentials_dir is not None:
            env["ATOMIC_MAIL_CREDENTIALS_DIR"] = credentials_dir

        server: dict[str, Any] = {
            "command": "npx",
            "args": ["-y", "@atomicmail/mcp"],
        }
        if env:
            server["env"] = env

        config_dict = {"mcpServers": {"atomicmail": server}}

        # Initialize parent MCPToolkit with Atomic Mail configuration
        super().__init__(config_dict=config_dict, timeout=timeout)
