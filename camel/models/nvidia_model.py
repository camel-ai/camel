# =========== Copyright 2024 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2024 @ CAMEL-AI.org. All Rights Reserved. ===========
import os
from typing import Any, Dict, List, Optional, Union, Generator

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion

from camel.configs import NVIDIA_API_PARAMS, NvidiaConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class NvidiaModel(BaseModelBackend):
    r"""NVIDIA API model backend implementation.

    This class provides an implementation of the NVIDIA API model backend,
    supporting various NVIDIA language models through their API.

    Args:
        model_type (Union[ModelType, str]): The type of NVIDIA model to use.
        model_config_dict (Optional[Dict[str, Any]], optional): Configuration
            dictionary for the model. If None, default NvidiaConfig will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): API key for NVIDIA API.
            If not provided, will look for NVIDIA_API_KEY environment variable.
            (default: :obj:`None`)
        url (Optional[str], optional): URL for the NVIDIA API.
            If not provided, will use default NVIDIA API URL.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter for
            the model. If not provided, will use OpenAITokenCounter.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = NvidiaConfig().as_dict()
        api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        url = url or os.environ.get(
            "NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        if token_counter is None:
            # Use gpt-4 for token counting as it's compatible with most models
            token_counter = OpenAITokenCounter(ModelType.GPT_4)
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._client = OpenAI(
            api_key=api_key,
            base_url=url,
            timeout=60,
            max_retries=3,
            default_headers={
                "accept": "application/json",
                "content-type": "application/json",
            },
        )

    def check_model_config(self) -> None:
        r"""Check if the model configuration contains any unexpected parameters.

        Raises:
            ValueError: If there are unexpected parameters in the configuration.
        """
        for param in self.model_config_dict:
            if param not in NVIDIA_API_PARAMS:
                raise ValueError(
                    f"Unexpected parameter '{param}' for NVIDIA API."
                )

    def token_counter(self, text: str) -> int:
        r"""Count the number of tokens in the given text.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The number of tokens in the text.
        """
        return self._token_counter.count_tokens(text)

    @api_keys_required("NVIDIA_API_KEY")
    def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Run the model with the given messages.

        Args:
            messages (List[Dict[str, str]]): List of messages for the conversation.
            stream (bool, optional): Whether to stream the response.
                (default: :obj:`False`)

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]: The model's response,
            either as a complete message or a stream of chunks.
        """
        # Override stream parameter if specified in config
        if 'stream' in self.model_config_dict:
            stream = self.model_config_dict['stream']

        # Prepare API parameters
        api_params = {
            "model": str(self.model_type),
            "messages": messages,
            "stream": stream,
            "max_tokens": self.model_config_dict.get('max_tokens', 1024),
            "temperature": self.model_config_dict.get('temperature', 0.5),
            "top_p": self.model_config_dict.get('top_p', 1.0),
            "frequency_penalty": self.model_config_dict.get('frequency_penalty', 0.0),
            "presence_penalty": self.model_config_dict.get('presence_penalty', 0.0),
            "seed": self.model_config_dict.get('seed', 0),
        }

        # Add optional parameters if specified
        if 'stop' in self.model_config_dict:
            api_params['stop'] = self.model_config_dict['stop']

        # Call the API
        response = self._client.chat.completions.create(**api_params)
        return response

    def _stream_response(self, response: Stream[ChatCompletion]) -> Generator[str, None, None]:
        """Process streaming response.

        Args:
            response: The streaming response from the model.

        Yields:
            The content of each chunk in the stream.
        """
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: Optional[bool] = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Chat with the model.

        Args:
            messages: A list of messages in the conversation.
            stream: Whether to stream the response.

        Returns:
            The model's response, either as a string or a generator of strings.
        """
        openai_messages = messages
        if stream is not None:
            self.model_config_dict['stream'] = stream
        
        response = self.run(openai_messages, stream=self.model_config_dict.get('stream', False))
        
        if not self.model_config_dict.get('stream', False):
            return response.choices[0].message.content
            
        return self._stream_response(response)
