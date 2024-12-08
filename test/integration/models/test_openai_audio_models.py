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
from unittest.mock import ANY, Mock, patch

from camel.models import OpenAIAudioModels
from camel.types import AudioModelType, VoiceType


def test_text_to_speech():
    openai_audio = OpenAIAudioModels()
    input_text = "Hello, world!"
    mock_response = Mock()
    mock_response.text = "Mock audio response"
    mock_client = Mock()
    mock_client.audio.speech.create.return_value = mock_response
    openai_audio._client = mock_client

    response = openai_audio.text_to_speech(input_text)

    assert response.text == "Mock audio response"
    mock_client.audio.speech.create.assert_called_once_with(
        model=AudioModelType.TTS_1.value,
        voice=VoiceType.ALLOY.value,
        input=input_text,
    )


def test_speech_to_text():
    openai_audio = OpenAIAudioModels()
    # Create a temporary audio file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(b'Test audio data')
        temp_file_path = temp_file.name

    mock_response = Mock()
    mock_response.text = "Mock transcription response"
    mock_client = Mock()
    mock_client.audio.transcriptions.create.return_value = mock_response
    openai_audio._client = mock_client

    response = openai_audio.speech_to_text(temp_file_path)

    assert response == "Mock transcription response"
    mock_client.audio.transcriptions.create.assert_called_once_with(
        model="whisper-1", file=ANY
    )

    # Clean up temporary file
    os.remove(temp_file_path)


@patch(
    "camel.models.openai_audio_models.os.path.getsize", return_value=1024
)  # Mocking the file size
@patch(
    "camel.models.openai_audio_models.open", new_callable=Mock
)  # Mocking the open function
def test_speech_to_text_large_audio(mock_open, mock_getsize):
    openai_audio = OpenAIAudioModels()
    audio_file_path = "large_audio.wav"
    mock_split_audio = Mock(return_value=["chunk1.wav", "chunk2.wav"])
    openai_audio._split_audio = mock_split_audio
    mock_response = Mock()
    mock_response.text = "Mock transcription response"
    mock_client = Mock()
    mock_client.audio.transcriptions.create.return_value = mock_response
    openai_audio._client = mock_client

    response = openai_audio.speech_to_text(audio_file_path)

    assert response == "Mock transcription response"
    assert mock_client.audio.transcriptions.create.call_count == 1
