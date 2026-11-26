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

from typing import Optional
from unittest.mock import patch

import pytest
from mcp.types import Tool

from camel.toolkits.notion_mcp_toolkit import NotionMCPToolkit
from camel.utils.mcp_client import TransportType


def test_interactive_route():
    toolkit = NotionMCPToolkit(17)
    (client,) = toolkit.clients
    assert client.config.timeout == 17
    assert client.transport_type == TransportType.STDIO
    assert client.config.command == "npx"
    assert client.config.args == [
        "-y",
        "mcp-remote@0.16.7",
        "https://mcp.notion.com/mcp",
    ]
    assert client.config.headers is None


def test_token_route():
    toolkit = NotionMCPToolkit(17, token="example-token")
    (client,) = toolkit.clients
    assert client.config.timeout == 17
    assert client.transport_type == TransportType.STREAMABLE_HTTP
    assert client.config.type == "streamable_http"
    assert client.config.url == "https://mcp.notion.com/mcp"
    assert client.config.headers == {"Authorization": "Bearer example-token"}
    assert client.config.command is None
    assert client.config.args is None


@pytest.mark.parametrize("token", ["", "   ", "example-token\n", "two tokens"])
def test_invalid_token(token: str):
    with pytest.raises(ValueError, match="token"):
        NotionMCPToolkit(token=token)


@pytest.mark.parametrize("token", [None, "example-token"])
def test_get_tools_preserves_nested_schema(token: Optional[str]):
    toolkit = NotionMCPToolkit(token=token)
    (client,) = toolkit.clients
    tool = Tool(
        name="find_page",
        description="Find a page.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "description": "Search query.",
                    "properties": {"name": {"type": "string"}},
                }
            },
        },
    )
    with (
        patch.object(client, "is_connected", return_value=True),
        patch.object(client, "_tools", [tool]),
    ):
        (function_tool,) = toolkit.get_tools()
    parameters = function_tool.get_openai_function_schema()["parameters"]
    assert parameters["properties"]["query"] == {
        "type": "object",
        "description": "Search query.",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }
