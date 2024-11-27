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

from camel.toolkits import RedditToolkit

# We need to mock the entire praw module
praw_mock = MagicMock()
praw_mock.Reddit = MagicMock()

# Apply the mock before importing RedditToolkit
with patch.dict('sys.modules', {'praw': praw_mock}):
    pass


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "fake_client_id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "fake_client_secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "fake_user_agent")


@pytest.fixture
def reddit_toolkit():
    with patch('praw.Reddit', new=praw_mock.Reddit):
        toolkit = RedditToolkit()
        # Manually set the reddit attribute
        toolkit._reddit = MagicMock()
        return toolkit


def test_collect_top_posts(reddit_toolkit):
    mock_subreddit = MagicMock()
    mock_post = MagicMock()
    mock_post.title = "Test Post Title"
    mock_comment = MagicMock()
    mock_comment.body = "Test Comment"
    mock_comment.score = 10
    mock_post.comments = [mock_comment]
    mock_subreddit.top.return_value = [mock_post]

    reddit_toolkit.reddit.subreddit.return_value = mock_subreddit

    result = reddit_toolkit.collect_top_posts("test_subreddit")

    expected_result = [
        {
            "Post Title": "Test Post Title",
            "Comments": [{"Comment Body": "Test Comment", "Upvotes": 10}],
        }
    ]
    assert result == expected_result


def test_perform_sentiment_analysis(reddit_toolkit):
    test_data = [
        {
            "Comment Body": "This is a great post!",
        }
    ]

    with patch("textblob.TextBlob") as mock_textblob:
        mock_textblob.return_value.sentiment.polarity = 0.9

        result = reddit_toolkit.perform_sentiment_analysis(test_data)

        expected_result = [
            {
                "Comment Body": "This is a great post!",
                "Sentiment Score": 0.9,
            }
        ]
        assert result == expected_result


def test_track_keyword_discussions(reddit_toolkit):
    mock_subreddit = MagicMock()
    mock_post = MagicMock()
    mock_post.title = "Test Post Title"
    mock_comment = MagicMock()
    mock_comment.body = "Discussing mental health here."
    mock_comment.score = 10
    mock_post.comments = [mock_comment]
    mock_subreddit.top.return_value = [mock_post]

    reddit_toolkit.reddit.subreddit.return_value = mock_subreddit

    with patch("textblob.TextBlob") as mock_textblob:
        mock_textblob.return_value.sentiment.polarity = -0.1

        result = reddit_toolkit.track_keyword_discussions(
            ["test_subreddit"], ["mental health"], sentiment_analysis=True
        )

        expected_result = [
            {
                "Subreddit": "test_subreddit",
                "Post Title": "Test Post Title",
                "Comment Body": "Discussing mental health here.",
                "Upvotes": 10,
                "Sentiment Score": -0.1,
            }
        ]

        assert result == expected_result


def test_get_tools(reddit_toolkit):
    from camel.toolkits import FunctionTool

    tools = reddit_toolkit.get_tools()
    assert len(tools) == 3
    assert all(isinstance(tool, FunctionTool) for tool in tools)
