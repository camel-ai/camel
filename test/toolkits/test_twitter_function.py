# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import TwitterToolkit


@pytest.fixture
def twitter_toolkit():
    return TwitterToolkit()


def test_create_tweet(monkeypatch, twitter_toolkit):
    # Create a mock response object
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'data': {
            'edit_history_tweet_ids': ['12345'],
            'id': '12345',
            'text': 'Test tweet',
        }
    }
    mock_response.status_code = 201

    # Mock user input to confirm creating a tweet
    monkeypatch.setattr('builtins.input', lambda _: 'yes')

    # Capture the output of the print function
    captured_output = []
    monkeypatch.setattr('builtins.print', lambda x: captured_output.append(x))

    # Use patch to mock the get_oauth_session method
    patch_path = (
        'camel.toolkits.twitter_toolkit.TwitterToolkit._get_oauth_session'
    )
    with patch(patch_path) as mock_get_oauth_session:
        # Configure the mock OAuth session's post method
        # to return the mock response object
        mock_get_oauth_session.return_value.post.return_value = mock_response

        # Call the create_tweet function
        response = twitter_toolkit.create_tweet(text="Test tweet.")

        # Verify the output
        expected_start = (
            "You are going to create a tweet with following parameters:"
        )
        assert expected_start in captured_output
        assert "text: Test tweet." in captured_output
        expected_response = (
            "Create tweet successful. The tweet ID is: "
            "12345. The tweet text is: 'Test tweet'."
        )
        assert response == expected_response


def test_delete_tweet(monkeypatch, twitter_toolkit):
    # Delete a mock response object
    mock_response = MagicMock()
    mock_response.json.return_value = {'data': {'deleted': True}}
    mock_response.status_code = 200

    # Mock user input to confirm creating a tweet
    monkeypatch.setattr('builtins.input', lambda _: 'yes')

    # Capture the output of the print function
    captured_output = []
    monkeypatch.setattr('builtins.print', lambda x: captured_output.append(x))

    # Use patch to mock the get_oauth_session method
    patch_path = (
        'camel.toolkits.twitter_toolkit.TwitterToolkit._get_oauth_session'
    )
    with patch(patch_path) as mock_get_oauth_session:
        # Configure the mock OAuth session's delete method
        # to return the mock response object
        mock_get_oauth_session.return_value.delete.return_value = mock_response

        # Call the delete_tweet function
        response = twitter_toolkit.delete_tweet(tweet_id="11111")

        # Verify the output
        expected_start = (
            "You are going to delete a tweet with the following ID: 11111"
        )
        assert expected_start in captured_output
        expected_response = (
            "Delete tweet successful: True. The tweet ID is: " "11111. "
        )
        assert response == expected_response


def test_get_user_me(monkeypatch, twitter_toolkit):
    # Mocked JSON response, anonymized
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
            'username': 'AUsername',
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

    # Use patch to mock the get_oauth_session method
    patch_path = (
        'camel.toolkits.twitter_toolkit.TwitterToolkit._get_oauth_session'
    )
    with patch(patch_path) as mock_get_oauth_session:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_json_response
        mock_response.status_code = 200
        mock_get_oauth_session.return_value.get.return_value = mock_response

        # Call the get_user_me function
        response = twitter_toolkit.get_my_user_profile()

        # Verify the returned user information report
        expected_report = (
            "ID: 1234567890. Name: A Name. Username: AUsername. "
            "Description: A description of the user.. Location: Some "
            "Location. "
            "Most recent tweet id: 1234567890123456789. "
            "Profile image url: https://example.com/image.jpg. "
            "Account created at: March 16, 2024 at 06:31:14. "
            "Protected: This user's Tweets are public. "
            "Verified type: The user is not verified. "
            "Public metrics: The user has 10 followers, "
            "is following 20 users, has made 30 tweets, "
            "is listed in 40 lists, and has received 50 likes. "
            "Pinned tweet ID: 9876543210987654321. "
            "\nPinned tweet information: Pinned tweet created at "
            "April 17, 2024 at 12:40:01 with text: 'A tweet content.'."
        )
        assert response == expected_report
