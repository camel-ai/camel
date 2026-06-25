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
import os
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import TwelveLabsToolkit


@pytest.fixture
def toolkit(monkeypatch):
    monkeypatch.setenv("TWELVELABS_API_KEY", "test-key")
    return TwelveLabsToolkit()


def test_get_tools(toolkit):
    tools = toolkit.get_tools()
    assert len(tools) == 2
    names = {tool.get_function_name() for tool in tools}
    assert names == {"ask_question_about_video", "summarize_video"}


def test_requires_a_video_source(toolkit):
    result = toolkit.ask_question_about_video(question="What happens?")
    assert result.startswith("Error")


@patch("twelvelabs.TwelveLabs")
def test_ask_question_about_video_url(mock_client_cls, toolkit):
    mock_client = MagicMock()
    mock_client.analyze.return_value = MagicMock(data="A cat plays piano.")
    mock_client_cls.return_value = mock_client

    result = toolkit.ask_question_about_video(
        question="What is in the video?",
        video_url="https://example.com/cat.mp4",
    )

    assert result == "A cat plays piano."
    mock_client.analyze.assert_called_once()
    kwargs = mock_client.analyze.call_args.kwargs
    assert kwargs["model_name"] == "pegasus1.5"
    assert kwargs["prompt"] == "What is in the video?"
    # URL inputs are passed via a VideoContext_Url object, not video_id.
    assert "video_id" not in kwargs
    assert kwargs["video"].url == "https://example.com/cat.mp4"


@patch("twelvelabs.TwelveLabs")
def test_summarize_video_by_id(mock_client_cls, toolkit):
    mock_client = MagicMock()
    mock_client.analyze.return_value = MagicMock(data="Summary text.")
    mock_client_cls.return_value = mock_client

    result = toolkit.summarize_video(video_id="vid_123")

    assert result == "Summary text."
    kwargs = mock_client.analyze.call_args.kwargs
    assert kwargs["video_id"] == "vid_123"
    assert "video" not in kwargs


@pytest.mark.skipif(
    not os.environ.get("TWELVELABS_API_KEY"),
    reason="TWELVELABS_API_KEY not set; skipping live API test.",
)
def test_live_ask_question_about_video():
    r"""Live smoke test against the real TwelveLabs Pegasus API.

    Uses a short public sample video. Skipped unless a real
    TWELVELABS_API_KEY is present in the environment.
    """
    toolkit = TwelveLabsToolkit()
    result = toolkit.ask_question_about_video(
        question="Describe what happens in this video in one sentence.",
        video_url=(
            "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/"
            "Big_Buck_Bunny_720_10s_1MB.mp4"
        ),
    )
    assert isinstance(result, str)
    assert not result.startswith("Error"), result
