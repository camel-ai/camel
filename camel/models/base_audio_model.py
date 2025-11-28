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
from abc import ABC, abstractmethod
from typing import Any, Optional

from camel.utils import Constants


class BaseAudioModel(ABC):
    r"""Base class for audio models providing Text-to-Speech (TTS) and
    Speech-to-Text (STT) functionality.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD,
    ) -> None:
        r"""Initialize an instance of BaseAudioModel.

        Args:
            api_key (Optional[str]): API key for the audio service. If not
                provided, will look for an environment variable specific to the
                implementation.
            url (Optional[str]): Base URL for the audio API. If not provided,
                will use a default URL or look for an environment variable
                specific to the implementation.
            timeout (Optional[float], optional): The timeout value in seconds
                for API calls. If not provided, will fall back to the
                MODEL_TIMEOUT environment variable or default to 180 seconds.
                (default: :obj:`None`)
        """
        self._api_key = api_key
        self._url = url
        self._timeout = timeout

    @abstractmethod
    def text_to_speech(
        self,
        input: str,
        *,
        storage_path: str,
        **kwargs: Any,
    ) -> Any:
        r"""Convert text to speech.

        Args:
            input (str): The text to be converted to speech.
            storage_path (str): The local path to store the
                generated speech file.
            **kwargs (Any): Extra kwargs passed to the TTS API.

        Returns:
            Any: The response from the TTS API, which may vary by
                implementation.
        """
        pass

    @abstractmethod
    def speech_to_text(
        self,
        audio_file_path: str,
        **kwargs: Any,
    ) -> str:
        r"""Convert speech audio to text.

        Args:
            audio_file_path (str): The audio file path to transcribe.
            **kwargs (Any): Extra keyword arguments passed to the
                Speech-to-Text (STT) API.

        Returns:
            str: The transcribed text.
        """
        pass

    def _ensure_directory_exists(self, file_path: str) -> None:
        r"""Ensure the directory for the given file path exists.

        Args:
            file_path (str): The file path for which to ensure the directory
                exists.
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
