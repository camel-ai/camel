# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import time
from unittest.mock import MagicMock, patch

import pytest


class TestCustomAzureCredential:
    """Tests for CustomAzureCredential behavior."""

    @pytest.fixture
    def credential(self, tmp_path):
        """Create a CustomAzureCredential instance for testing."""
        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            CustomAzureCredential,
        )

        return CustomAzureCredential(
            client_id="test_client_id",
            client_secret="test_client_secret",
            tenant_id="test_tenant_id",
            refresh_token="test_refresh_token",
            scopes=["Scope_1"],
            refresh_token_file_path=tmp_path / "token.json",
        )

    def test_returns_valid_access_token_after_refresh(self, credential):
        """When token is expired, get_token should refresh and return
        a valid AccessToken.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
        }

        with patch("requests.post", return_value=mock_response):
            token = credential.get_token()

        assert token.token == "new_access_token"
        assert token.expires_on > int(time.time())

    def test_caches_token_until_expiry(self, credential):
        """get_token should return cached token without refreshing
        if not expired.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "cached_token",
            "expires_in": 3600,
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            # First call - should refresh
            token1 = credential.get_token()
            # Second call - should use cache
            token2 = credential.get_token()

        # Should only call the API once
        assert mock_post.call_count == 1
        assert token1.token == token2.token == "cached_token"

    def test_refreshes_token_when_expired(self, credential):
        """get_token should refresh when the cached token is expired."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "expires_in": 3600,
        }

        with patch("requests.post", return_value=mock_response):
            # First call to get initial token
            credential.get_token()

        # Simulate token expiry
        credential._expires_at = int(time.time()) - 1

        mock_response.json.return_value = {
            "access_token": "new_refreshed_token",
            "expires_in": 3600,
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            token = credential.get_token()

        assert mock_post.call_count == 1
        assert token.token == "new_refreshed_token"

    def test_saves_new_refresh_token_when_provided(self, credential, tmp_path):
        """When Microsoft returns a new refresh token, it should be saved."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access_token",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token",
        }

        with patch("requests.post", return_value=mock_response):
            credential.get_token()

        # Verify token was saved to file
        token_file = tmp_path / "token.json"
        assert token_file.exists()
        with open(token_file) as f:
            saved_data = json.load(f)
        assert saved_data["refresh_token"] == "new_refresh_token"

    def test_raises_exception_on_token_refresh_failure(self, credential):
        """get_token should raise an exception when token refresh fails."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Refresh token expired",
        }

        with (
            patch("requests.post", return_value=mock_response),
            pytest.raises(Exception, match="Token refresh failed"),
        ):
            credential.get_token()


class TestMicrosoftAuthenticator:
    """Tests for MicrosoftAuthenticator behavior."""

    @pytest.fixture
    def authenticator(self, tmp_path):
        """Create a MicrosoftAuthenticator instance for testing."""
        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            MicrosoftAuthenticator,
        )

        return MicrosoftAuthenticator(
            scopes=["Scope_1"],
            refresh_token_file_path=tmp_path / "token.json",
        )

    def test_generates_dynamic_redirect_uri(self, authenticator):
        """Redirect URI should be a valid localhost URL with a port."""
        assert authenticator.redirect_uri.startswith("http://localhost:")
        port = int(authenticator.redirect_uri.split(":")[-1])
        assert port >= 1

    def test_loads_token_from_valid_file(self, authenticator, tmp_path):
        """Should successfully load refresh token from a valid file."""
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"refresh_token": "saved_token"}))

        token = authenticator._load_token_from_file()

        assert token == "saved_token"

    def test_loads_token_returns_none_when_token_file_missing(self, tmp_path):
        """Should return None when token file does not exist."""
        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            MicrosoftAuthenticator,
        )

        authenticator = MicrosoftAuthenticator(
            scopes=["Scope_1"],
            refresh_token_file_path=tmp_path / "nonexistent.json",
        )

        token = authenticator._load_token_from_file()

        assert token is None

    def test_loads_token_returns_none_when_no_token_file_path(self):
        """Should return None when no token file path is configured."""
        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            MicrosoftAuthenticator,
        )

        authenticator = MicrosoftAuthenticator(
            scopes=["Scope_1"],
            refresh_token_file_path=None,
        )

        token = authenticator._load_token_from_file()

        assert token is None

    def test_loads_token_returns_none_when_token_file_missing_key(
        self, authenticator, tmp_path
    ):
        """Should return None when token file is missing refresh_token key."""
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"other_key": "value"}))

        token = authenticator._load_token_from_file()

        assert token is None

    def test_saves_token_to_file(self, authenticator, tmp_path):
        """Should save refresh token to the configured file path."""
        authenticator._save_token_to_file("new_token")

        token_file = tmp_path / "token.json"
        assert token_file.exists()
        with open(token_file) as f:
            saved_data = json.load(f)
        assert saved_data["refresh_token"] == "new_token"

    def test_constructs_valid_auth_url(self, authenticator):
        """Auth URL should contain all required OAuth parameters."""
        authenticator.client_id = "test_client"
        authenticator.tenant_id = "test_tenant"

        auth_url = authenticator._get_auth_url(
            client_id="test_client",
            tenant_id="test_tenant",
            redirect_uri="http://localhost:8000",
            scopes=["Scope_1", "Scope_2"],
        )

        assert "login.microsoftonline.com" in auth_url
        assert "test_tenant" in auth_url
        assert "test_client" in auth_url
        # to check if scopes are separated properly
        assert "Scope_1+Scope_2" in auth_url
        assert "response_type=code" in auth_url

    def test_authenticate_uses_refresh_token_when_available(
        self, authenticator, tmp_path
    ):
        """Should use refresh token authentication when token file exists."""
        # Setup: Create a token file
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"refresh_token": "saved_token"}))

        with patch.dict(
            'os.environ',
            {
                'MICROSOFT_CLIENT_ID': 'test_client',
                'MICROSOFT_CLIENT_SECRET': 'test_secret',
            },
        ):
            # Mock the refresh token auth to succeed
            with patch.object(
                authenticator,
                '_authenticate_using_refresh_token',
                return_value=MagicMock(),
            ) as mock_refresh_auth:
                credentials = authenticator.authenticate()

            mock_refresh_auth.assert_called_once()
            assert credentials is not None

    def test_authenticate_falls_back_to_browser_on_refresh_failure(
        self, authenticator, tmp_path
    ):
        """Should fall back to browser auth when refresh token fails."""
        # Setup: Create a token file
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"refresh_token": "invalid_token"}))

        with patch.dict(
            'os.environ',
            {
                'MICROSOFT_CLIENT_ID': 'test_client',
                'MICROSOFT_CLIENT_SECRET': 'test_secret',
            },
        ):
            # Mock refresh token to fail
            with (
                patch.object(
                    authenticator,
                    '_authenticate_using_refresh_token',
                    side_effect=ValueError("Token expired"),
                ),
                patch.object(
                    authenticator,
                    '_authenticate_using_browser',
                    return_value=MagicMock(),
                ) as mock_browser_auth,
            ):
                credentials = authenticator.authenticate()

            mock_browser_auth.assert_called_once()
            assert credentials is not None

    def test_authenticate_uses_browser_when_no_token_file(self, tmp_path):
        """Should use browser auth when no token file exists."""
        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            MicrosoftAuthenticator,
        )

        authenticator = MicrosoftAuthenticator(
            scopes=["Scope_1"],
            refresh_token_file_path=tmp_path / "nonexistent.json",
        )

        with patch.dict(
            'os.environ',
            {
                'MICROSOFT_CLIENT_ID': 'test_client',
                'MICROSOFT_CLIENT_SECRET': 'test_secret',
            },
        ):
            with patch.object(
                authenticator,
                '_authenticate_using_browser',
                return_value=MagicMock(),
            ) as mock_browser_auth:
                credentials = authenticator.authenticate()

            mock_browser_auth.assert_called_once()
            assert credentials is not None

    def test_creates_graph_client_with_credentials(self, authenticator):
        """Should create a GraphServiceClient with provided credentials."""
        mock_credentials = MagicMock()

        with patch("msgraph.GraphServiceClient") as mock_client_class:
            mock_client_class.return_value = MagicMock()

            client = authenticator.get_graph_client(
                credentials=mock_credentials,
                scopes=["Scope_1"],
            )

            mock_client_class.assert_called_once_with(
                credentials=mock_credentials,
                scopes=["Scope_1"],
            )
            assert client is not None

    def test_raises_error_when_graph_client_creation_fails(
        self, authenticator
    ):
        """Should raise ValueError when Graph client creation fails."""
        mock_credentials = MagicMock()

        with (
            patch(
                "msgraph.GraphServiceClient",
                side_effect=Exception("Connection error"),
            ),
            pytest.raises(ValueError, match="Failed to create Graph client"),
        ):
            authenticator.get_graph_client(
                credentials=mock_credentials,
                scopes=["Scope_1"],
            )


class TestRedirectHandler:
    """Tests for RedirectHandler behavior."""

    def test_extracts_authorization_code_from_request(self):
        """Should extract auth code from OAuth redirect request."""
        from io import BytesIO

        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            RedirectHandler,
        )

        # Create mock server
        mock_server = MagicMock()
        mock_server.code = None

        handler = RedirectHandler.__new__(RedirectHandler)
        handler.path = "/?code=test_auth_code&state=xyz"
        handler.server = mock_server
        handler.requestline = "GET /?code=test_auth_code HTTP/1.1"
        handler.request_version = "HTTP/1.1"
        handler.wfile = BytesIO()
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()

        assert mock_server.code == "test_auth_code"

    def test_handles_missing_code_correctly(self):
        """Should handle requests without auth code."""
        from io import BytesIO

        from camel.toolkits.microsoft_outlook_toolkits._auth_utils import (
            RedirectHandler,
        )

        mock_server = MagicMock()
        mock_server.code = None

        handler = RedirectHandler.__new__(RedirectHandler)
        handler.path = "/?error=access_denied"
        handler.server = mock_server
        handler.requestline = "GET /?error=access_denied HTTP/1.1"
        handler.request_version = "HTTP/1.1"
        handler.wfile = BytesIO()
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()

        # Code should be None when not present
        assert mock_server.code is None
