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
import time
from pathlib import Path
from typing import Any, Optional

import requests

from camel.models.base_audio_model import BaseAudioModel

_MODELSLAB_TTS_URL = "https://modelslab.com/api/v6/voice/text_to_speech"
_MODELSLAB_TTS_FETCH_URL = "https://modelslab.com/api/v6/voice/fetch/{request_id}"
_DEFAULT_POLL_INTERVAL = 5  # seconds
_DEFAULT_TIMEOUT = 300  # seconds


class ModelsLabAudioModel(BaseAudioModel):
    r"""Provides access to ModelsLab's Text-to-Speech (TTS) API.

    ModelsLab (https://modelslab.com) is an AI generation platform supporting
    text-to-image, video, and audio generation. This model provides TTS access
    using key-in-body authentication and asynchronous polling.

    Args:
        api_key (Optional[str]): API key for ModelsLab. If not provided,
            uses the ``MODELSLAB_API_KEY`` environment variable.
        url (Optional[str]): Base URL for ModelsLab TTS API. Defaults to the
            official endpoint.
        voice_id (int): Voice ID to use for generation. Defaults to ``1``
            (neutral voice). Available IDs: 1 (neutral), 2 (male),
            3 (warm male), 4 (deep male), 5 (female), 6 (clear female).
        language (str): Language for TTS. Defaults to ``"english"``.
        speed (float): Speech speed (0.5–2.0). Defaults to ``1.0``.

    Notes:
        ModelsLab uses key-in-body authentication — the API key is sent
        in the JSON request body, not in the Authorization header.

        The API is asynchronous: it may return ``status: processing`` with
        a ``request_id``, requiring polling of the fetch endpoint until
        ``status: success``.

    Example:
        >>> from camel.models import ModelsLabAudioModel
        >>> model = ModelsLabAudioModel(
        ...     api_key="your_api_key",
        ...     voice_id=5,  # Female voice
        ...     language="english",
        ... )
        >>> model.text_to_speech("Hello from CAMEL!", storage_path="output.mp3")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        voice_id: int = 1,
        language: str = "english",
        speed: float = 1.0,
    ) -> None:
        super().__init__(api_key, url)
        self._api_key = api_key or os.environ.get("MODELSLAB_API_KEY")
        if self._api_key is None:
            raise ValueError(
                "API key is required for ModelsLab. Please provide it via "
                "the 'api_key' parameter or set the 'MODELSLAB_API_KEY' "
                "environment variable."
            )
        self._url = url or _MODELSLAB_TTS_URL
        self._voice_id = voice_id
        self._language = language
        self._speed = speed

    def text_to_speech(
        self,
        input: str,
        *,
        storage_path: str,
        voice_id: Optional[int] = None,
        language: Optional[str] = None,
        speed: Optional[float] = None,
        **kwargs: Any,
    ) -> bytes:
        r"""Convert text to speech and save it to a file.

        ModelsLab's API may return an audio URL immediately
        (``status: success``) or require polling (``status: processing``).
        This method handles both cases transparently.

        Args:
            input (str): The text to convert to speech.
            storage_path (str): Local file path to save the audio output.
            voice_id (Optional[int]): Override the default voice ID.
            language (Optional[str]): Override the default language.
            speed (Optional[float]): Override the default speed.
            **kwargs: Additional parameters passed to the TTS API.

        Returns:
            bytes: The raw audio bytes saved to ``storage_path``.

        Raises:
            ValueError: If the API returns an error status.
            requests.HTTPError: If the HTTP request fails.
        """
        body = {
            "key": self._api_key,
            "prompt": input,
            "language": language or self._language,
            "voice_id": voice_id or self._voice_id,
            "speed": speed or self._speed,
            **kwargs,
        }

        response = requests.post(
            self._url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "error":
            raise ValueError(
                f"ModelsLab TTS error: {data.get('message', 'Unknown error')}"
            )

        if data.get("status") == "processing":
            request_id = str(data.get("request_id", ""))
            if not request_id:
                raise ValueError(
                    "ModelsLab TTS returned processing status without request_id"
                )
            data = self._poll_until_ready(request_id)

        audio_url = data.get("output", "")
        if not audio_url:
            raise ValueError("ModelsLab TTS returned no audio URL")

        # Download the audio file
        audio_resp = requests.get(audio_url, timeout=self._timeout)
        audio_resp.raise_for_status()
        audio_bytes = audio_resp.content

        # Ensure the parent directory exists
        self._ensure_directory_exists(storage_path)
        Path(storage_path).write_bytes(audio_bytes)

        return audio_bytes

    def speech_to_text(
        self,
        audio_file_path: str,
        **kwargs: Any,
    ) -> str:
        r"""Convert speech to text.

        .. note::
            ModelsLab does not provide a speech-to-text API.
            This method raises :obj:`NotImplementedError`.

        Args:
            audio_file_path (str): Unused.
            **kwargs: Unused.

        Raises:
            NotImplementedError: Always raised.
        """
        raise NotImplementedError(
            "ModelsLab does not support speech-to-text. "
            "Use a different provider for STT, such as OpenAIAudioModels."
        )

    def _poll_until_ready(
        self,
        request_id: str,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict:
        r"""Poll the ModelsLab fetch endpoint until the audio is ready.

        Args:
            request_id (str): The request ID returned by the TTS API.
            poll_interval (float): Seconds between polls. (default: :obj:`5`)
            timeout (float): Max seconds to wait. (default: :obj:`300`)

        Returns:
            dict: The final API response with ``status: success``.

        Raises:
            TimeoutError: If the audio is not ready within ``timeout`` seconds.
            ValueError: If the API returns ``status: error``.
        """
        fetch_url = _MODELSLAB_TTS_FETCH_URL.format(request_id=request_id)
        body = {"key": self._api_key}
        deadline = time.time() + timeout

        while time.time() < deadline:
            time.sleep(poll_interval)
            resp = requests.post(
                fetch_url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "error":
                raise ValueError(
                    f"ModelsLab TTS failed: {data.get('message', 'Unknown error')}"
                )
            if data.get("status") == "success":
                return data
            # status == "processing" → keep polling

        raise TimeoutError(
            f"ModelsLab TTS timed out after {timeout}s (request_id={request_id})"
        )
