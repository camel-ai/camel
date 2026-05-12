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
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from camel.models import ModelsLabAudioModel


def test_modelslab_audio_model_init_from_env():
    r"""Test initialization using environment variable for API key."""
    with patch.dict(os.environ, {"MODELSLAB_API_KEY": "test_env_key"}):
        model = ModelsLabAudioModel()
        assert model._api_key == "test_env_key"


def test_modelslab_audio_model_init_with_key():
    r"""Test initialization with explicit API key."""
    model = ModelsLabAudioModel(api_key="explicit_key")
    assert model._api_key == "explicit_key"


def test_modelslab_audio_model_init_defaults():
    r"""Test that default voice parameters are set correctly."""
    model = ModelsLabAudioModel(api_key="test_key")
    assert model._voice_id == 1
    assert model._language == "english"
    assert model._speed == 1.0


def test_modelslab_audio_model_init_missing_key():
    r"""Test that ValueError is raised when no API key is available."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove MODELSLAB_API_KEY if it exists
        env = {k: v for k, v in os.environ.items() if k != "MODELSLAB_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                ModelsLabAudioModel()


def test_modelslab_audio_model_text_to_speech_immediate_success(tmp_path):
    r"""Test text_to_speech when API returns success immediately."""
    mock_audio_bytes = b"fake_audio_data"

    mock_tts_response = MagicMock()
    mock_tts_response.raise_for_status = MagicMock()
    mock_tts_response.json.return_value = {
        "status": "success",
        "output": "https://example.com/audio.mp3",
    }

    mock_audio_response = MagicMock()
    mock_audio_response.raise_for_status = MagicMock()
    mock_audio_response.content = mock_audio_bytes

    output_path = str(tmp_path / "output.mp3")

    with patch("requests.post", return_value=mock_tts_response), patch(
        "requests.get", return_value=mock_audio_response
    ):
        model = ModelsLabAudioModel(api_key="test_key")
        result = model.text_to_speech(
            input="Hello CAMEL!", storage_path=output_path
        )

    assert result == mock_audio_bytes
    assert Path(output_path).read_bytes() == mock_audio_bytes


def test_modelslab_audio_model_text_to_speech_with_polling(tmp_path):
    r"""Test text_to_speech when API returns processing then success."""
    mock_audio_bytes = b"polled_audio_data"
    output_path = str(tmp_path / "output.mp3")

    mock_tts_response = MagicMock()
    mock_tts_response.raise_for_status = MagicMock()
    mock_tts_response.json.return_value = {
        "status": "processing",
        "request_id": 42,
    }

    mock_poll_response = MagicMock()
    mock_poll_response.raise_for_status = MagicMock()
    mock_poll_response.json.return_value = {
        "status": "success",
        "output": "https://example.com/audio.mp3",
    }

    mock_audio_response = MagicMock()
    mock_audio_response.raise_for_status = MagicMock()
    mock_audio_response.content = mock_audio_bytes

    with patch("requests.post") as mock_post, patch(
        "requests.get", return_value=mock_audio_response
    ), patch("time.sleep"):
        # First call → TTS initiation; subsequent calls → polling
        mock_post.side_effect = [mock_tts_response, mock_poll_response]
        model = ModelsLabAudioModel(api_key="test_key")
        result = model.text_to_speech(
            input="Hello CAMEL!", storage_path=output_path
        )

    assert result == mock_audio_bytes


def test_modelslab_audio_model_text_to_speech_api_error():
    r"""Test that ValueError is raised on API error response."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "status": "error",
        "message": "Invalid API key",
    }

    with patch("requests.post", return_value=mock_response):
        model = ModelsLabAudioModel(api_key="bad_key")
        with pytest.raises(ValueError, match="ModelsLab TTS error"):
            model.text_to_speech(
                input="Hello!", storage_path="/tmp/output.mp3"
            )


def test_modelslab_audio_model_text_to_speech_no_audio_url(tmp_path):
    r"""Test that ValueError is raised when no audio URL is returned."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "success", "output": ""}

    with patch("requests.post", return_value=mock_response):
        model = ModelsLabAudioModel(api_key="test_key")
        with pytest.raises(ValueError, match="no audio URL"):
            model.text_to_speech(
                input="Hello!", storage_path=str(tmp_path / "output.mp3")
            )


def test_modelslab_audio_model_speech_to_text_not_implemented():
    r"""Test that speech_to_text raises NotImplementedError."""
    model = ModelsLabAudioModel(api_key="test_key")
    with pytest.raises(NotImplementedError):
        model.speech_to_text("some_audio.wav")


def test_modelslab_audio_model_poll_timeout():
    r"""Test that TimeoutError is raised when polling exceeds timeout."""
    mock_tts_response = MagicMock()
    mock_tts_response.raise_for_status = MagicMock()
    mock_tts_response.json.return_value = {
        "status": "processing",
        "request_id": 99,
    }

    mock_poll_response = MagicMock()
    mock_poll_response.raise_for_status = MagicMock()
    mock_poll_response.json.return_value = {"status": "processing"}

    with patch("requests.post") as mock_post, patch("time.sleep"), patch(
        "time.time"
    ) as mock_time:
        # Simulate timeout: time.time() starts at 0, immediately jumps past
        # deadline
        mock_time.side_effect = [0, 0, 1000]
        mock_post.side_effect = [mock_tts_response, mock_poll_response]
        model = ModelsLabAudioModel(api_key="test_key")
        with pytest.raises(TimeoutError):
            model._poll_until_ready("99", poll_interval=1, timeout=5)
