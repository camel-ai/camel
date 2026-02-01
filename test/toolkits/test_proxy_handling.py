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

"""Unit tests for proxy handling in WebSocketBrowserWrapper."""

import os
import pytest

from camel.toolkits.hybrid_browser_toolkit.ws_wrapper import WebSocketBrowserWrapper


class TestProxyHandling:
    """Test proxy environment variable handling in WebSocketBrowserWrapper."""

    @pytest.mark.asyncio
    async def test_proxy_disabled_by_default(self):
        """Test that proxy is disabled for localhost by default."""
        wrapper = WebSocketBrowserWrapper(config={})

        assert wrapper.disable_proxy_for_localhost is True

    @pytest.mark.asyncio
    async def test_proxy_can_be_enabled_explicitly(self):
        """Test that proxy can be explicitly enabled via config."""
        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': False}
        )

        assert wrapper.disable_proxy_for_localhost is False

    @pytest.mark.asyncio
    async def test_proxy_disabled_explicitly(self):
        """Test that proxy can be explicitly disabled."""
        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': True}
        )

        assert wrapper.disable_proxy_for_localhost is True

    @pytest.mark.asyncio
    async def test_proxy_context_manager_removes_vars(self):
        """Test that context manager removes proxy variables."""
        # Set proxy variables
        os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
        os.environ['HTTPS_PROXY'] = 'http://proxy.example.com:8080'
        os.environ['http_proxy'] = 'http://proxy.example.com:8080'
        os.environ['https_proxy'] = 'http://proxy.example.com:8080'

        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': True}
        )

        # Enter context manager
        async with wrapper._proxy_context_manager():
            # Verify proxy variables are removed
            assert 'HTTP_PROXY' not in os.environ
            assert 'HTTPS_PROXY' not in os.environ
            assert 'http_proxy' not in os.environ
            assert 'https_proxy' not in os.environ

        # Verify restoration
        assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'
        assert os.environ['HTTPS_PROXY'] == 'http://proxy.example.com:8080'
        assert os.environ['http_proxy'] == 'http://proxy.example.com:8080'
        assert os.environ['https_proxy'] == 'http://proxy.example.com:8080'

        # Cleanup
        del os.environ['HTTP_PROXY']
        del os.environ['HTTPS_PROXY']
        del os.environ['http_proxy']
        del os.environ['https_proxy']

    @pytest.mark.asyncio
    async def test_proxy_context_manager_with_no_proxy_set(self):
        """Test context manager when no proxy is set."""
        # Ensure no proxy variables
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(var, None)

        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': True}
        )

        # Should not raise exception
        async with wrapper._proxy_context_manager():
            # No proxy variables should be present
            assert 'HTTP_PROXY' not in os.environ
            assert 'HTTPS_PROXY' not in os.environ

    @pytest.mark.asyncio
    async def test_proxy_context_manager_when_disabled(self):
        """Test that context manager does nothing when proxy handling disabled."""
        os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
        os.environ['HTTPS_PROXY'] = 'http://proxy.example.com:8080'

        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': False}
        )

        # Proxy should remain unchanged
        async with wrapper._proxy_context_manager():
            assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'
            assert os.environ['HTTPS_PROXY'] == 'http://proxy.example.com:8080'

        # Should still be present after context exit
        assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'
        assert os.environ['HTTPS_PROXY'] == 'http://proxy.example.com:8080'

        # Cleanup
        del os.environ['HTTP_PROXY']
        del os.environ['HTTPS_PROXY']

    @pytest.mark.asyncio
    async def test_proxy_context_manager_exception_safety(self):
        """Test that proxy vars are restored even if exception occurs."""
        os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
        os.environ['HTTPS_PROXY'] = 'http://proxy.example.com:8080'

        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': True}
        )

        # Raise exception inside context
        with pytest.raises(ValueError, match="Test exception"):
            async with wrapper._proxy_context_manager():
                # Verify proxy is removed inside context
                assert 'HTTP_PROXY' not in os.environ
                assert 'HTTPS_PROXY' not in os.environ
                raise ValueError("Test exception")

        # Verify restoration despite exception
        assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'
        assert os.environ['HTTPS_PROXY'] == 'http://proxy.example.com:8080'

        # Cleanup
        del os.environ['HTTP_PROXY']
        del os.environ['HTTPS_PROXY']

    @pytest.mark.asyncio
    async def test_proxy_context_manager_partial_proxy_vars(self):
        """Test context manager when only some proxy vars are set."""
        # Set only some proxy variables
        os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)

        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': True}
        )

        async with wrapper._proxy_context_manager():
            # All should be removed
            assert 'HTTP_PROXY' not in os.environ
            assert 'HTTPS_PROXY' not in os.environ
            assert 'http_proxy' not in os.environ
            assert 'https_proxy' not in os.environ

        # Only HTTP_PROXY should be restored
        assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'
        assert 'HTTPS_PROXY' not in os.environ
        assert 'http_proxy' not in os.environ
        assert 'https_proxy' not in os.environ

        # Cleanup
        del os.environ['HTTP_PROXY']

    @pytest.mark.asyncio
    async def test_proxy_context_manager_multiple_entries(self):
        """Test that context manager can be entered multiple times."""
        os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'

        wrapper = WebSocketBrowserWrapper(
            config={'disable_proxy_for_localhost': True}
        )

        # First entry
        async with wrapper._proxy_context_manager():
            assert 'HTTP_PROXY' not in os.environ

        # Should be restored
        assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'

        # Second entry
        async with wrapper._proxy_context_manager():
            assert 'HTTP_PROXY' not in os.environ

        # Should be restored again
        assert os.environ['HTTP_PROXY'] == 'http://proxy.example.com:8080'

        # Cleanup
        del os.environ['HTTP_PROXY']
