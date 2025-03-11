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
from unittest.mock import MagicMock, patch

from camel.models import FishAudioModel


def test_fish_audio_model_init():
    r"""Test initialization of FishAudioModel."""
    # Test with no API key or URL, should use environment variables
    with patch.dict(
        os.environ,
        {
            "FISHAUDIO_API_KEY": "test_api_key",
            "FISHAUDIO_API_BASE_URL": "https://api.fish.audio",
        },
    ):
        model = FishAudioModel()
        assert model._api_key == "test_api_key"
        assert model._url == "https://api.fish.audio"


def test_fish_audio_model_text_to_speech_no_reference_audio():
    r"""Test text_to_speech with no reference audio."""
    # Mock the session's TTS method to avoid actual API calls
    with patch("fish_audio_sdk.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session
        mock_session.tts.return_value = [b"audio_data"]

        model = FishAudioModel(
            api_key="test_api_key", url="https://api.fish.audio"
        )

        with patch("builtins.open") as mock_file:
            mock_file.return_value.__enter__.return_value.write = MagicMock()

            model.text_to_speech(input="Hello", storage_path="output_path.wav")

            mock_session.tts.assert_called_once()
            mock_file.return_value.__enter__.return_value.write.assert_called_once_with(
                b"audio_data"
            )


def test_fish_audio_model_text_to_speech_with_reference_audio():
    r"""Test text_to_speech with reference audio."""
    with patch("fish_audio_sdk.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session
        mock_session.tts.return_value = [b"audio_data"]

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", patch_open := MagicMock()),
        ):
            patch_open.return_value.__enter__.return_value.read = MagicMock(
                return_value=b"reference_audio_data"
            )

            model = FishAudioModel(
                api_key="test_api_key", url="https://api.fish.audio"
            )

            model.text_to_speech(
                input="Hello",
                storage_path="output_path.wav",
                reference_audio="reference_audio.wav",
                reference_audio_text="Reference text",
            )

            mock_session.tts.assert_called_once()


def test_fish_audio_model_speech_to_text():
    r"""Test speech_to_text method."""
    with patch("fish_audio_sdk.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session
        mock_session.asr.return_value = MagicMock(text="Hello world")

        with patch("builtins.open", patch_open := MagicMock()):
            patch_open.return_value.__enter__.return_value.read = MagicMock(
                return_value=b"audio_data"
            )
            with patch("os.path.exists", return_value=True):
                model = FishAudioModel(
                    api_key="test_api_key", url="https://api.fish.audio"
                )

                result = model.speech_to_text("audio_file.wav")

                assert result == "Hello world"
                mock_session.asr.assert_called_once()


def test_fish_audio_model_speech_to_text_file_not_found():
    r"""Test speech_to_text raises FileNotFoundError."""
    # Create instance of FishAudioModel
    model = FishAudioModel(
        api_key="test_api_key", url="https://api.fish.audio"
    )

    # Test that the method raises FileNotFoundError if file doesn't exist
    with patch("os.path.exists", return_value=False):
        try:
            model.speech_to_text("non_existent_file.wav")
        except FileNotFoundError as e:
            assert str(e) == "Audio file not found: non_existent_file.wav"
