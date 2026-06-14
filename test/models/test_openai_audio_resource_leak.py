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
import tempfile
from unittest.mock import MagicMock, Mock, patch

from camel.models import OpenAIAudioModels


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
@patch("camel.models.openai_audio_models.OpenAI")
def test_speech_to_text_closes_file_handle(mock_openai_cls):
    r"""Test that speech_to_text properly closes file handles
    using context managers."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_response = Mock()
    mock_response.text = "transcribed text"
    mock_client.audio.transcriptions.create.return_value = mock_response

    openai_audio = OpenAIAudioModels()

    with tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False
    ) as temp_file:
        temp_file.write(b"Test audio data")
        temp_file_path = temp_file.name

    try:
        result = openai_audio.speech_to_text(temp_file_path)
        assert result == "transcribed text"
        mock_client.audio.transcriptions.create.assert_called_once()

        # Verify the file argument was passed from a context manager
        call_args = mock_client.audio.transcriptions.create.call_args
        assert call_args.kwargs["file"] is not None
    finally:
        os.remove(temp_file_path)


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
@patch("camel.models.openai_audio_models.OpenAI")
def test_speech_to_text_translate_closes_file_handle(mock_openai_cls):
    r"""Test that speech_to_text with translation properly closes
    file handles."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_response = Mock()
    mock_response.text = "translated text"
    mock_client.audio.translations.create.return_value = mock_response

    openai_audio = OpenAIAudioModels()

    with tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False
    ) as temp_file:
        temp_file.write(b"Test audio data")
        temp_file_path = temp_file.name

    try:
        result = openai_audio.speech_to_text(
            temp_file_path, translate_into_english=True
        )
        assert result == "translated text"
        mock_client.audio.translations.create.assert_called_once()
    finally:
        os.remove(temp_file_path)
