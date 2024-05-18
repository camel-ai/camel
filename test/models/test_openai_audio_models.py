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
import io
from unittest.mock import Mock, patch

import pytest

from camel.models import OpenAIAudioModels


def test_text_to_speech_success():
    openai = OpenAIAudioModels()
    openai._client.audio.speech.create = Mock(return_value="Mock response")

    response = openai.text_to_speech("Hello, world!")

    assert response == "Mock response"


def test_text_to_speech_error():
    openai = OpenAIAudioModels()
    openai._client.audio.speech.create = Mock(
        side_effect=Exception("Test Exception")
    )

    with pytest.raises(Exception):
        openai.text_to_speech("Hello, world!")


@patch("builtins.open", return_value=io.BytesIO(b"mock audio data"))
def test_speech_to_text_success(mock_open):
    openai = OpenAIAudioModels()
    openai._client.audio.transcriptions.create = Mock(
        return_value=Mock(text="Hello, world!")
    )

    response = openai.speech_to_text("test_audio.wav")

    assert response == "Hello, world!"


@patch("builtins.open", return_value=io.BytesIO(b"mock audio data"))
def test_speech_to_text_translate_success(mock_open):
    openai = OpenAIAudioModels()
    openai._client.audio.translations.create = Mock(
        return_value=Mock(text="Bonjour le monde!")
    )

    response = openai.speech_to_text("test_audio.wav", translate_into_eng=True)

    assert response == "Bonjour le monde!"


def test_speech_to_text_unsupported_format():
    openai = OpenAIAudioModels()

    with pytest.raises(ValueError):
        openai.speech_to_text("test_audio.xyz")


def test_speech_to_text_error():
    openai = OpenAIAudioModels()
    openai._client.audio.transcriptions.create = Mock(
        side_effect=Exception("Test Exception")
    )

    with pytest.raises(Exception):
        openai.speech_to_text("test_audio.wav")
