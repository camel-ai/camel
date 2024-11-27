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
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import LinkedInToolkit


@pytest.fixture
def linkedin_toolkit(monkeypatch):
    # Mock _get_access_token method to return a fake token
    monkeypatch.setattr(
        LinkedInToolkit, "_get_access_token", lambda self: "fake_token"
    )
    return LinkedInToolkit()


def test_create_post(monkeypatch, linkedin_toolkit):
    # Mock the profile response including the ID
    mock_profile = {'id': 'urn:li:person:test-id'}
    monkeypatch.setattr(
        linkedin_toolkit, 'get_profile', lambda include_id: mock_profile
    )

    # Create a mock response object for post creation
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'id': 'urn:li:share:7234172587444953088'
    }
    mock_response.status_code = 201

    # Mock the post request
    with patch('requests.post') as mock_post:
        mock_post.return_value = mock_response

        # Call the create_post function
        response = linkedin_toolkit.create_post(
            text="A post created by LinkedInToolkit @Camel."
        )

        # Verify the output
        expected_response = {
            'Post ID': 'urn:li:share:7234172587444953088',
            'Text': 'A post created by LinkedInToolkit @Camel.',
        }
        assert response == expected_response


def test_delete_post(monkeypatch, linkedin_toolkit):
    # Mock the delete response
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.NO_CONTENT

    # Mock the input function to simulate user confirmation
    monkeypatch.setattr('builtins.input', lambda _: 'yes')

    # Mock the delete request
    with patch('requests.delete') as mock_delete:
        mock_delete.return_value = mock_response

        # Call the delete_post function
        response = linkedin_toolkit.delete_post(
            post_id="urn:li:share:7234172587444953088"
        )

        # Verify the output
        expected_response = (
            "Post deleted successfully. Post ID: "
            "urn:li:share:7234172587444953088."
        )
        assert response == expected_response


def test_get_profile(linkedin_toolkit):
    # Mock the profile response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'locale': {'country': 'US', 'language': 'en'},
        'given_name': 'Neil',
        'family_name': 'John',
        'email': 'canning1157822807@gmail.com',
        'sub': 'test-id',
    }
    mock_response.status_code = HTTPStatus.OK

    # Mock the get request
    with patch('requests.get') as mock_get:
        mock_get.return_value = mock_response

        # Call the get_profile function with include_id=True
        response = linkedin_toolkit.get_profile(include_id=True)

        # Verify the output
        expected_report = {
            'Country': 'US',
            'Language': 'en',
            'First Name': 'Neil',
            'Last Name': 'John',
            'Email': 'canning1157822807@gmail.com',
            'id': 'urn:li:person:test-id',
        }
        assert response == expected_report
