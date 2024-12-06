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


class FishAudioModel:
    r"""Provides access to FishAudio's Text-to-Speech (TTS) and Speech_to_Text
    (STT) models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        r"""Initialize an instance of OpenAI."""
        from fish_audio_sdk import Session

        self._url = url or os.environ.get(
            "FISHAUDIO_API_BASE_URL", "https://api.fish.audio"
        )
        self._api_key = api_key or os.environ.get("FISHAUDIO_API_KEY")
        self.session = Session(apikey=self._api_key, base_url=self._url)

    def text_to_speech(
        self,
        input: str,
        storage_path: str,
        reference_id: str = "MODEL_ID_UPLOADED_OR_CHOSEN_FROM_PLAYGROUND",
        reference_audio: str = "",
        **kwargs: Any,
    ) -> Any:
        r""" """
        from fish_audio_sdk import ReferenceAudio, TTSRequest

        if not reference_audio:
            with open(f"{storage_path}.mp3", "wb") as f:
                for chunk in self.session.tts(
                    TTSRequest(reference_id=reference_id, text=input, **kwargs)
                ):
                    f.write(chunk)
        else:
            with open(f"{reference_audio}.mp3", "rb") as audio_file:
                with open(f"{storage_path}.mp3", "wb") as f:
                    for chunk in self.session.tts(
                        TTSRequest(
                            text=input,
                            references=[
                                ReferenceAudio(
                                    audio=audio_file.read(),
                                    text="Text in reference audio",
                                    **kwargs,
                                )
                            ],
                        )
                    ):
                        f.write(chunk)

    def speech_to_text(
        self,
        audio_file_path: str,
        language: str,
        ignore_timestamps: bool,
        **kwargs: Any,
    ) -> str:
        r""" """
        from fish_audio_sdk import ASRRequest

        with open(f"{audio_file_path}.mp3", "rb") as audio_file:
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
