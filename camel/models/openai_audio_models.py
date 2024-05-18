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
import os
import io

from typing import Any
from openai import OpenAI

from camel.types import AudioModelType, VoiceType

class OpenAIAudioModels():
    r"""Provides access to OpenAI's Text-to-Speech (TTS) and Speech_to_Text
    (STT) models."""

    def __init__(
        self,
        ) -> None:
        r"""Initialize an instance of OpenAI."""
        url = os.environ.get('OPENAI_API_BASE_URL')
        self._client = OpenAI(timeout=60, max_retries=3, base_url=url)

    def text_to_speech(self,
                       input:str,
                       model_type: AudioModelType = AudioModelType.TTS_1,
                       voice: VoiceType = VoiceType.ALLOY,
                       **kwargs: Any,
                       ) -> Any:
        r"""Convert text to speech using OpenAI's TTS model. This method
        converts the given input text to speech using the specified model and
        voice.

        Args:
            input (str): The text to be converted to speech.
            model_type (AudioModelType, optional): The TTS model to use.
                Defaults to `AudioModelType.TTS_1`.
            voice (VoiceType, optional): The voice to be used for generating
                speech. Defaults to `VoiceType.ALLOY`.
            **kwargs (Any): Extra kwargs passed to the TTS API.

        Returns:
            Response content object from OpenAI.

        Raises:
            Exception: If there's an error during the TTS API call.
        """
        try:
            response = self._client.audio.speech.create(
                model=model_type.value,
                voice=voice.value,
                input=input,
                **kwargs,
            )
            return response
        except Exception as e:
            raise Exception("Error during TTS API call") from e

    def speech_to_text(self, audio_file_path: str, translate_into_eng: bool = False, **kwargs: Any) -> str:
        r"""Convert speech audio to text.

        Args:
            audio_file_path (str): The audio file path, supporting one of
                these formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
            translate_into_eng (bool, optional): Whether to translate the
                speech into English. Defaults to `False`.
            **kwargs (Any): Extra keyword arguments passed to the
                Speech-to-Text (STT) API.

        Returns:
            str: The output text.

        Raises:
            ValueError: If the audio file format is not supported.
            Exception: If there's an error during the STT API call.
        """
        supported_formats = ["flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"]
        file_format = audio_file_path.split(".")[-1].lower()

        if file_format not in supported_formats:
            raise ValueError(f"Unsupported audio file format: {file_format}")

        with open(audio_file_path, "rb") as audio_file:
            audio_data = io.BytesIO(audio_file.read())

        try:
            if translate_into_eng:
                translation = self._client.audio.translations.create(
                    model="whisper-1",
                    file=audio_data,
                    **kwargs
                )
                return translation.text
            else:
                transcription = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_data,
                    **kwargs
                )
                return transcription.text
        except Exception as e:
            raise Exception("Error during STT API call") from e
