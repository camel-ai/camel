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
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from camel.utils.mcp import MCPServerMixin


def fake_fastmcp_constructor(*args, **kwargs):
    fake_fastmcp_constructor.created_args = kwargs
    instance = MagicMock(spec=FastMCP)

    def fake_tool_decorator(method):
        fake_tool_decorator.called_methods.append(method)
        return method

    fake_tool_decorator.called_methods = []
    instance.tool.return_value = fake_tool_decorator
    instance.run = lambda transport: None
    instance._created_args = fake_fastmcp_constructor.created_args
    return instance


@pytest.fixture
def mock_fastmcp(monkeypatch):
    monkeypatch.setattr('mcp.server.fastmcp.FastMCP', fake_fastmcp_constructor)
    monkeypatch.setattr('camel.utils.mcp.FastMCP', fake_fastmcp_constructor)
    instance = fake_fastmcp_constructor()
    return instance


@pytest.fixture
def server_class(mock_fastmcp):
    class TestServer(MCPServerMixin):
        _mcp_instance = mock_fastmcp

        def public_method(self):
            return "public"

        def _private_method(self):
            return "private"

    return TestServer


class TestMCPServerMixin:
    def test_register_mcp_tools(self, server_class, mock_fastmcp):
        server_class._register_mcp_tools(server_class)
        registered_methods = mock_fastmcp.tool.return_value.called_methods
        public_names = [m.__name__ for m in registered_methods]
        assert (
            'public_method' in public_names
        ), f"registered_methods: {public_names}"
        assert all(not m.__name__.startswith('_') for m in registered_methods)

    @pytest.mark.parametrize("transport", ["stdio", "sse"])
    def test_start_mcp_server(self, server_class, monkeypatch, transport):
        server_class._mcp_instance = None
        server_class.start_mcp_server(transport=transport)
        new_instance = server_class._mcp_instance
        assert new_instance._created_args.get("name") == server_class.__name__

    def test_register_tools_without_instance(self):
        class BrokenServer(MCPServerMixin):
            _mcp_instance = None

            def public_method(self):
                pass

        with pytest.raises(
            AssertionError, match="_mcp_instance must be initialized"
        ):
            BrokenServer._register_mcp_tools(BrokenServer)

    def test_fastmcp_name_is_subclass_name(self, monkeypatch):
        monkeypatch.setattr(
            'mcp.server.fastmcp.FastMCP', fake_fastmcp_constructor
        )
        monkeypatch.setattr(
            'camel.utils.mcp.FastMCP', fake_fastmcp_constructor
        )

        class CustomNamedServer(MCPServerMixin):
            def echo(self):
                return "hi"

        CustomNamedServer._mcp_instance = None
        CustomNamedServer.start_mcp_server()
        assert (
            fake_fastmcp_constructor.created_args.get("name")
            == "CustomNamedServer"
        )
