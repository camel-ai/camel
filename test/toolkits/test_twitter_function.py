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
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits.twitter_toolkit import (
    create_tweet,
    delete_tweet,
    get_my_user_profile,
    get_user_by_username,
)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("TWITTER_CONSUMER_KEY", "12345")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "12345")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "12345")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "12345")


def test_create_tweet(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'data': {
            'edit_history_tweet_ids': ['12345'],
            'id': '12345',
            'text': 'Test tweet',
        }
    }
    mock_response.status_code = 201

    with patch(
        "camel.toolkits.twitter_toolkit.requests.post"
    ) as mock_requests_post:
        mock_requests_post.return_value = mock_response

        # Call the create_tweet function
        response = create_tweet("Test tweet.")

        expected_response = (
            "Create tweet 12345 successful with content Test tweet."
        )
        assert response == expected_response


def test_delete_tweet(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {'data': {'deleted': True}}
    mock_response.status_code = 200

    with patch(
        "camel.toolkits.twitter_toolkit.requests.delete"
    ) as mock_requests_delete:
        mock_requests_delete.return_value = mock_response

        response = delete_tweet("11111")
        expected_response = "Delete tweet 11111 successful."
        assert response == expected_response


def test_get_user_me(monkeypatch):
    mock_response = MagicMock()
    mock_json_response = {
        'data': {
            'location': 'Some Location',
            'most_recent_tweet_id': '1234567890123456789',
            'pinned_tweet_id': '9876543210987654321',
            'description': 'A description of the user.',
            'name': 'A Name',
            'protected': False,
            'verified_type': 'none',
            'id': '1234567890',
            'username': 'myusername',
            'public_metrics': {
                'followers_count': 10,
                'following_count': 20,
                'tweet_count': 30,
                'listed_count': 40,
                'like_count': 50,
            },
            'profile_image_url': 'https://example.com/image.jpg',
            'created_at': '2024-03-16T06:31:14.000Z',
        },
        'includes': {
            'tweets': [
                {
                    'id': '9876543210987654321',
                    'created_at': '2024-04-17T12:40:01.000Z',
                    'text': 'A tweet content.',
                }
            ]
        },
    }
    mock_response.json.return_value = mock_json_response
    mock_response.status_code = 200

    with patch(
        "camel.toolkits.twitter_toolkit.requests.get"
    ) as mock_requests_get:
        mock_requests_get.return_value = mock_response
        response = get_my_user_profile()

        # Verify the returned user information report
        expected_report = textwrap.dedent(
            """\
            ID: 1234567890
            Name: A Name
            Username: myusername
            Description: A description of the user.
            Location: Some Location
            Most recent tweet id: 1234567890123456789
            Profile image url: https://example.com/image.jpg
            Account created at: March 16, 2024 at 06:31:14
            Protected: This user's Tweets are public
            Verified type: The user is not verified
            Public metrics: The user has 10 followers, is following 20 users, has made 30 tweets, is listed in 40 lists, and has received 50 likes
            Pinned tweet ID: 9876543210987654321
            Pinned tweet information: Pinned tweet created at April 17, 2024 at 12:40:01 with text: 'A tweet content.'
            """  # noqa: E501
        )

        assert response.strip() == expected_report.strip()


def test_get_user_by_username(monkeypatch):
    mock_response = MagicMock()
    mock_json_response = {
        'data': {
            'location': 'Another Location',
            'most_recent_tweet_id': '1234567890123456789',
            'pinned_tweet_id': '9876543210987654321',
            'description': 'A description of another user.',
            'name': 'A Name',
            'protected': False,
            'verified_type': 'none',
            'id': '1234567890',
            'username': 'anotherusername',
            'public_metrics': {
                'followers_count': 10,
                'following_count': 20,
                'tweet_count': 30,
                'listed_count': 40,
                'like_count': 50,
            },
            'profile_image_url': 'https://example.com/image.jpg',
            'created_at': '2024-03-16T06:31:14.000Z',
        },
        'includes': {
            'tweets': [
                {
                    'id': '9876543210987654321',
                    'created_at': '2024-04-17T12:40:01.000Z',
                    'text': 'A tweet content.',
                }
            ]
        },
    }
    mock_response.json.return_value = mock_json_response
    mock_response.status_code = 200

    with patch(
        "camel.toolkits.twitter_toolkit.requests.get"
    ) as mock_requests_get:
        mock_requests_get.return_value = mock_response
        response = get_user_by_username("anotherusername")

        # Verify the returned user information report
        expected_report = textwrap.dedent(
            """\
            ID: 1234567890
            Name: A Name
            Username: anotherusername
            Description: A description of another user.
            Location: Another Location
            Most recent tweet id: 1234567890123456789
            Profile image url: https://example.com/image.jpg
            Account created at: March 16, 2024 at 06:31:14
            Protected: This user's Tweets are public
            Verified type: The user is not verified
            Public metrics: The user has 10 followers, is following 20 users, has made 30 tweets, is listed in 40 lists, and has received 50 likes
            Pinned tweet ID: 9876543210987654321
            Pinned tweet information: Pinned tweet created at April 17, 2024 at 12:40:01 with text: 'A tweet content.'
            """  # noqa: E501
        )

        assert response.strip() == expected_report.strip()
