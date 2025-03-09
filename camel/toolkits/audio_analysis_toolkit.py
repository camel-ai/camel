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
import base64
import os
from typing import List, Optional
from urllib.parse import urlparse

import requests

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, OpenAIAudioModels
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.logger import get_logger

logger = get_logger(__name__)


class AudioAnalysisToolkit(BaseToolkit):
    r"""A class representing a toolkit for audio operations.

    This class provides methods for processing and understanding audio data.

    Args:
        cache_dir (Optional[str]): Directory path for caching audio files.
            Defaults to 'tmp/' if not specified.
        transcribe_model (Optional[OpenAIAudioModels]): Model used for audio transcription.
            Must be provided, otherwise raises ValueError.
        audio_reasoning_model (Optional[BaseModelBackend]): Model used for audio reasoning
            and question answering. If not provided, uses default model in ChatAgent.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        # reasoning: Optional[bool] = False,
        transcribe_model: Optional[OpenAIAudioModels] = None,
        audio_reasoning_model: Optional[BaseModelBackend] = None,
    ):
        self.cache_dir = 'tmp/'
        if cache_dir:
            self.cache_dir = cache_dir

        # self.client = openai.OpenAI()
        if transcribe_model is None:
            raise ValueError("Transcribe Model not Initialized")
        # self.reasoning = reasoning
        self.transcribe_model = transcribe_model
        self.audio_reasoning_model = audio_reasoning_model
        from camel.agents import ChatAgent
        if self.audio_reasoning_model:
            self.audio_agent = ChatAgent(model=self.audio_reasoning_model)
        else:
            self.audio_agent = ChatAgent()
            logger.warning(
                "No audio reasoning model provided. Using default model in"
                " ChatAgent."
            )

    def audio2text(self, audio_path: str) -> str:
        r"""Transcribe audio to text.

        Args:
            audio_path (str): The path to the audio file or URL.

        Returns:
            str: The transcribed text.
        """
        logger.debug(
            f"Calling transcribe_audio method for audio file `{audio_path}`."
        )

        if self.transcribe_model is None:
            logger.warning("Audio transcription is disabled or not available")
            return "No audio transcription available."

        try:
            audio_transcript = self.transcribe_model.speech_to_text(audio_path)
            if not audio_transcript:
                logger.warning("Audio transcription returned empty result")
                return "No audio transcription available."
            return audio_transcript
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return "Audio transcription failed."

    def ask_question_about_audio(self, audio_path: str, question: str) -> str:
        r"""Ask any question about the audio and get the answer using
            multimodal model.

        Args:
            audio_path (str): The path to the audio file.
            question (str): The question to ask about the audio.

        Returns:
            str: The answer to the question.
        """

        logger.debug(
            f"Calling ask_question_about_audio method for audio file \
            `{audio_path}` and question `{question}`."
        )

        parsed_url = urlparse(audio_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])
        encoded_string = None

        if is_url:
            res = requests.get(audio_path)
            res.raise_for_status()
            audio_data = res.content
            encoded_string = base64.b64encode(audio_data).decode('utf-8')
        else:
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()
            audio_file.close()
            encoded_string = base64.b64encode(audio_data).decode('utf-8')

        file_suffix = os.path.splitext(audio_path)[1]
        file_format = file_suffix[1:]

        # if self.reasoning:
        # text_prompt = f"Transcribe all the content in the speech into text."
        transcript = self.audio2text(audio_path)
        reasoning_prompt = f"""
        <speech_transcription_result>{transcript}</speech_transcription_result>

        Please answer the following question based on the speech transcription result above:
        <question>{question}</question>
        """
        msg = BaseMessage.make_user_message(
            role_name="User", content=reasoning_prompt
        )
        # response = self.audio_reasoning_model.chat_completion(msg)
        response = self.audio_agent.step(msg)
        # reasoning_result = response.choices[0].message.content
        if not response or not response.msgs:
            logger.error("Model returned empty response")
            return (
                "Failed to generate an answer. "
                "The model returned an empty response."
            )

        answer = response.msgs[0].content
        return answer

        # @mengkang: The following part is to answer a question directly use a audio model. We need to refactor the openai_audio_models.py to support this.
        # else:
        #     text_prompt = f"""Answer the following question based on the given \
        #     audio information:\n\n{question}"""

        #     completion = self.client.chat.completions.create(
        #         # model="gpt-4o-audio-preview",
        #         model = "gpt-4o-mini-audio-preview",
        #         messages=[
        #             {
        #                 "role": "system",
        #                 "content": "You are a helpful assistant specializing in \
        #                 audio analysis.",
        #             },
        #             {  # type: ignore[list-item, misc]
        #                 "role": "user",
        #                 "content": [
        #                     {"type": "text", "text": text_prompt},
        #                     {
        #                         "type": "input_audio",
        #                         "input_audio": {
        #                             "data": encoded_string,
        #                             "format": file_format,
        #                         },
        #                     },
        #                 ],
        #             },
        #         ],
        #     )  # type: ignore[misc]

        # response: str = str(completion.choices[0].message.content)
        # logger.debug(f"Response: {response}")
        # return str(response)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
            in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_question_about_audio),
            FunctionTool(self.audio2text),
        ]
