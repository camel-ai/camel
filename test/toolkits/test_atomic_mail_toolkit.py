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
"""Tests for AtomicMailToolkit."""

from camel.toolkits import AtomicMailToolkit
from camel.toolkits.mcp_toolkit import MCPToolkit


class TestAtomicMailToolkit:
    """Test AtomicMailToolkit configuration."""

    def test_is_mcp_toolkit(self):
        """The toolkit is an MCPToolkit and starts disconnected."""
        toolkit = AtomicMailToolkit()
        assert isinstance(toolkit, MCPToolkit)
        assert not toolkit.is_connected

    def test_default_server_command(self):
        """The default configuration runs the published npm package."""
        toolkit = AtomicMailToolkit()
        config = toolkit.clients[0].config

        assert len(toolkit.clients) == 1
        assert config.command == "npx"
        assert config.args == ["-y", "@atomicmail/mcp"]

    def test_no_env_by_default(self):
        """Without credentials nothing is forced into the server env."""
        toolkit = AtomicMailToolkit()
        assert not getattr(toolkit.clients[0].config, "env", None)

    def test_api_key_is_passed_through_env(self):
        """An existing inbox key reaches the server as ATOMIC_MAIL_API_KEY."""
        toolkit = AtomicMailToolkit(api_key="test-key")
        env = toolkit.clients[0].config.env

        assert env["ATOMIC_MAIL_API_KEY"] == "test-key"
        assert "ATOMIC_MAIL_CREDENTIALS_DIR" not in env

    def test_credentials_dir_is_passed_through_env(self):
        """A credentials directory reaches the server."""
        toolkit = AtomicMailToolkit(credentials_dir="/tmp/inbox-a")
        env = toolkit.clients[0].config.env

        assert env["ATOMIC_MAIL_CREDENTIALS_DIR"] == "/tmp/inbox-a"
        assert "ATOMIC_MAIL_API_KEY" not in env

    def test_both_credentials_are_passed(self):
        """Both values are forwarded when both are given."""
        toolkit = AtomicMailToolkit(
            api_key="test-key", credentials_dir="/tmp/inbox-b"
        )
        env = toolkit.clients[0].config.env

        assert env["ATOMIC_MAIL_API_KEY"] == "test-key"
        assert env["ATOMIC_MAIL_CREDENTIALS_DIR"] == "/tmp/inbox-b"

    def test_separate_instances_keep_separate_inboxes(self):
        """Two instances can drive two inboxes from one process."""
        support = AtomicMailToolkit(credentials_dir="/tmp/support")
        billing = AtomicMailToolkit(credentials_dir="/tmp/billing")

        support_env = support.clients[0].config.env
        billing_env = billing.clients[0].config.env

        assert support_env["ATOMIC_MAIL_CREDENTIALS_DIR"] == "/tmp/support"
        assert billing_env["ATOMIC_MAIL_CREDENTIALS_DIR"] == "/tmp/billing"

    def test_timeout_is_forwarded(self):
        """The timeout reaches the parent MCPToolkit."""
        toolkit = AtomicMailToolkit(timeout=30.0)
        assert toolkit.timeout == 30.0
