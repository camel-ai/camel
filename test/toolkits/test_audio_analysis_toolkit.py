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
import os
import tempfile
from unittest.mock import MagicMock, patch

from camel.messages import BaseMessage
from camel.models import OpenAIAudioModels
from camel.toolkits.audio_analysis_toolkit import (
    AudioAnalysisToolkit,
    download_file,
)


def test_download_file():
    r"""Test the download_file function with a mock response."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with (
            patch('requests.get') as mock_get,
            patch('requests.head') as mock_head,
        ):
            # Mock the head request to get content type
            mock_head_response = MagicMock()
            mock_head_response.headers = {'Content-Type': 'audio/mpeg'}
            mock_head.return_value = mock_head_response

            # Mock the get request for downloading
            mock_response = MagicMock()
            mock_response.iter_content.return_value = [b'test audio content']
            mock_get.return_value = mock_response

            # Test with URL that has a filename
            url = 'http://example.com/audio.mp3'
            result = download_file(url, temp_dir)

            # Verify the file was created with expected path
            assert os.path.exists(result)
            assert os.path.basename(result) == 'audio.mp3'

            # Test with URL that doesn't have a filename
            url = 'http://example.com/audio'
            result = download_file(url, temp_dir)

            # Verify a file was created
            assert os.path.exists(result)
            # The file should exist in the temp directory
            assert temp_dir in result


def test_audio2text():
    r"""Test the audio2text method of AudioAnalysisToolkit."""
    # Create mock transcribe model
    mock_model = MagicMock(spec=OpenAIAudioModels)
    mock_model.speech_to_text.return_value = "This is a test transcription."

    # Create toolkit with mock model
    toolkit = AudioAnalysisToolkit(transcribe_model=mock_model)

    # Test successful transcription
    result = toolkit.audio2text("test_audio.mp3")
    assert result == "This is a test transcription."
    mock_model.speech_to_text.assert_called_once_with("test_audio.mp3")

    # Test exception handling
    mock_model.speech_to_text.side_effect = Exception("Test error")
    result = toolkit.audio2text("test_audio.mp3")
    assert result == "Audio transcription failed."


def test_ask_question_about_audio_direct():
    r"""Test ask_question_about_audio method with direct audio question
    answering.
    """
    # Create mock transcribe model with audio_question_answering method
    mock_model = MagicMock(spec=OpenAIAudioModels)
    mock_model.audio_question_answering.return_value = (
        "The answer to your question."
    )

    # Create toolkit with mock model
    toolkit = AudioAnalysisToolkit(transcribe_model=mock_model)

    # Test with local audio file
    result = toolkit.ask_question_about_audio(
        "test_audio.mp3", "What is in the audio?"
    )
    assert result == "The answer to your question."
    mock_model.audio_question_answering.assert_called_once_with(
        "test_audio.mp3", "What is in the audio?"
    )


def test_ask_question_about_audio_fallback():
    r"""Test ask_question_about_audio method with fallback to transcription."""
    # Create mock transcribe model without audio_question_answering
    mock_model = MagicMock(spec=OpenAIAudioModels)
    mock_model.audio_question_answering.side_effect = Exception(
        "Not implemented"
    )
    mock_model.speech_to_text.return_value = "This is a test transcription."

    # Create mock chat agent
    mock_agent = MagicMock()
    mock_response = MagicMock()
    mock_response.msgs = [MagicMock(content="Answer based on transcription.")]
    mock_agent.step.return_value = mock_response

    # Create toolkit with mocks
    with patch('camel.agents.ChatAgent') as MockChatAgent:
        MockChatAgent.return_value = mock_agent
        toolkit = AudioAnalysisToolkit(transcribe_model=mock_model)

        # Test fallback to transcription
        result = toolkit.ask_question_about_audio(
            "test_audio.mp3", "What is in the audio?"
        )
        assert result == "Answer based on transcription."
        mock_model.speech_to_text.assert_called_once_with("test_audio.mp3")
        mock_agent.step.assert_called_once()
        # Verify the message passed to the agent contains the transcript and
        # question
        msg = mock_agent.step.call_args[0][0]
        assert isinstance(msg, BaseMessage)
        assert "speech_transcription_result" in msg.content
        assert "What is in the audio?" in msg.content


def test_ask_question_about_audio_url():
    r"""Test ask_question_about_audio method with URL input."""
    # Create mock transcribe model
    mock_model = MagicMock(spec=OpenAIAudioModels)
    mock_model.audio_question_answering.return_value = (
        "The answer to your question."
    )

    # Create toolkit with mock model
    with patch(
        'camel.toolkits.audio_analysis_toolkit.download_file'
    ) as mock_download:
        mock_download.return_value = "/tmp/downloaded_audio.mp3"
        toolkit = AudioAnalysisToolkit(transcribe_model=mock_model)

        # Test with URL
        url = "http://example.com/audio.mp3"
        result = toolkit.ask_question_about_audio(url, "What is in the audio?")
        assert result == "The answer to your question."
        mock_download.assert_called_once_with(url, toolkit.cache_dir)
        mock_model.audio_question_answering.assert_called_once_with(
            "/tmp/downloaded_audio.mp3", "What is in the audio?"
        )


def test_get_tools():
    r"""Test the get_tools method of AudioAnalysisToolkit."""
    toolkit = AudioAnalysisToolkit()
    tools = toolkit.get_tools()

    # Verify we have the expected number of tools
    assert len(tools) == 2

    # Verify the tool functions
    tool_functions = [tool.func for tool in tools]
    assert toolkit.ask_question_about_audio in tool_functions
    assert toolkit.audio2text in tool_functions
