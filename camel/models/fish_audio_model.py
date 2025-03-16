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
from typing import Any, Optional

from camel.models.base_audio_model import BaseAudioModel


class FishAudioModel(BaseAudioModel):
    r"""Provides access to FishAudio's Text-to-Speech (TTS) and Speech_to_Text
    (STT) models.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        r"""Initialize an instance of FishAudioModel.

        Args:
            api_key (Optional[str]): API key for FishAudio service. If not
                provided, the environment variable `FISHAUDIO_API_KEY` will be
                used.
            url (Optional[str]): Base URL for FishAudio API. If not provided,
                the environment variable `FISHAUDIO_API_BASE_URL` will be used.
        """
        from fish_audio_sdk import Session

        super().__init__(api_key, url)
        self._api_key = api_key or os.environ.get("FISHAUDIO_API_KEY")
        self._url = url or os.environ.get(
            "FISHAUDIO_API_BASE_URL", "https://api.fish.audio"
        )
        self.session = Session(apikey=self._api_key, base_url=self._url)

    def text_to_speech(
        self,
        input: str,
        *,
        storage_path: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_audio: Optional[str] = None,
        reference_audio_text: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        r"""Convert text to speech and save the output to a file.

        Args:
            input (str): The text to convert to speech.
            storage_path (Optional[str]): The file path where the resulting
                speech will be saved. (default: :obj:`None`)
            reference_id (Optional[str]): An optional reference ID to
                associate with the request. (default: :obj:`None`)
            reference_audio (Optional[str]): Path to an audio file for
                reference speech. (default: :obj:`None`)
            reference_audio_text (Optional[str]): Text for the reference audio.
                (default: :obj:`None`)
            **kwargs (Any): Additional parameters to pass to the TTS request.

        Raises:
            FileNotFoundError: If the reference audio file cannot be found.
            ValueError: If storage_path is not provided or if reference_audio
                is provided without reference_audio_text.
        """
        from fish_audio_sdk import ReferenceAudio, TTSRequest

        if storage_path is None:
            raise ValueError(
                "storage_path must be provided for "
                "FishAudioModel.text_to_speech"
            )

        self._ensure_directory_exists(storage_path)

        if not reference_audio:
            with open(f"{storage_path}", "wb") as f:
                for chunk in self.session.tts(
                    TTSRequest(reference_id=reference_id, text=input, **kwargs)
                ):
                    f.write(chunk)
        else:
            if not os.path.exists(reference_audio):
                raise FileNotFoundError(
                    f"Reference audio file not found: {reference_audio}"
                )
            if not reference_audio_text:
                raise ValueError("reference_audio_text should be provided")
            with open(f"{reference_audio}", "rb") as audio_file:
                with open(f"{storage_path}", "wb") as f:
                    for chunk in self.session.tts(
                        TTSRequest(
                            text=input,
                            references=[
                                ReferenceAudio(
                                    audio=audio_file.read(),
                                    text=reference_audio_text,
                                )
                            ],
                            **kwargs,
                        )
                    ):
                        f.write(chunk)

    def speech_to_text(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        ignore_timestamps: Optional[bool] = None,
        **kwargs: Any,
    ) -> str:
        r"""Convert speech to text from an audio file.

        Args:
            audio_file_path (str): The path to the audio file to transcribe.
            language (Optional[str]): The language of the audio. (default:
                :obj:`None`)
            ignore_timestamps (Optional[bool]): Whether to ignore timestamps.
                (default: :obj:`None`)
            **kwargs (Any): Additional parameters to pass to the STT request.

        Returns:
            str: The transcribed text from the audio.

        Raises:
            FileNotFoundError: If the audio file cannot be found.
        """
        from fish_audio_sdk import ASRRequest

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        with open(f"{audio_file_path}", "rb") as audio_file:
            audio_data = audio_file.read()

        response = self.session.asr(
            ASRRequest(
                audio=audio_data,
                language=language,
                ignore_timestamps=ignore_timestamps,
                **kwargs,
            )
        )
        return response.text
