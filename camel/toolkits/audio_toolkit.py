from typing import List, Optional, Any, Dict
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.messages import BaseMessage
import librosa
import openai
import os
from retry import retry

from io import BytesIO
from urllib.request import urlopen
from loguru import logger
from pydub import AudioSegment
from urllib.parse import urlparse
import requests
import base64


class AudioToolkit(BaseToolkit):
    r"""A class representing a toolkit for audio operations.

    This class provides methods for processing and understanding audio data.
    """
    def __init__(self, cache_dir: str = None):

        self.cache_dir = 'tmp/'
        if cache_dir:
            self.cache_dir = cache_dir

        self.audio_client = openai.OpenAI()
    

    def ask_question_about_audio(self, audio_path: str, question: str) -> str:
        r"""Ask any question about the audio and get the answer using multimodal model.

        Args:
            audio_path (str): The path to the audio file.
            question (str): The question to ask about the audio.

        Returns:
            str: The answer to the question.
        """

        logger.debug(f"Calling ask_question_about_audio method for audio file `{audio_path}` and question `{question}`.")

        parsed_url = urlparse(audio_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])
        encoded_string = None

        if is_url:
            response = requests.get(url)
            response.raise_for_status()
            audio_data = response.content
            encoded_string = base64.b64encode(audio_data).decode('utf-8')
        else:
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()
            audio_file.close()
            encoded_string = base64.b64encode(audio_data).decode('utf-8')
        
        file_suffix = os.path.splitext(audio_path)[1]
        file_format = file_suffix[1:]

        text_prompt = f"""Answer the following question based on the given audio information:\n\n{question}"""
        
        completion = self.audio_client.chat.completions.create(
            model="gpt-4o-mini-audio-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant specializing in audio analysis."
                },
                {
                    "role": "user",
                    "content": [
                        { 
                            "type": "text",
                            "text": text_prompt
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": encoded_string,
                                "format": file_format
                            }
                        }
                    ]
                },
            ]
        )

        response = completion.choices[0].message.content
        logger.debug(f"Response: {response}")
        return response


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_question_about_audio)
        ]

