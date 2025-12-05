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

from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import OutlookCalendarToolkit

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_graph_client():
    """Mock Microsoft Graph API client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def outlook_calendar_toolkit(mock_graph_client):
    """Fixture that provides a mocked OutlookCalendarToolkit instance."""
    mock_credentials = MagicMock()
    mock_credentials.valid = True

    # Mock the MicrosoftAuthenticator used inside OutlookCalendarToolkit
    mock_authenticator = MagicMock()
    mock_authenticator.authenticate.return_value = mock_credentials
    mock_authenticator.get_graph_client.return_value = mock_graph_client

    with (
        patch.dict(
            'os.environ',
            {
                'MICROSOFT_TENANT_ID': 'mock_tenant_id',
                'MICROSOFT_CLIENT_ID': 'mock_client_id',
                'MICROSOFT_CLIENT_SECRET': 'mock_client_secret',
            },
        ),
        patch(
            'camel.toolkits.microsoft_outlook_toolkits'
            '.microsoft_outlook_calendar_toolkit.MicrosoftAuthenticator',
            return_value=mock_authenticator,
        ),
    ):
        toolkit = OutlookCalendarToolkit()
        yield toolkit
