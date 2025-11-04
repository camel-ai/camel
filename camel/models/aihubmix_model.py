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
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs.aihubmix_config import AihubmixConfig
from camel.messages import OpenAIMessage
from camel.models.anthropic_model import AnthropicModel
from camel.models.base_model import BaseModelBackend
from camel.models.gemini_model import GeminiModel
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.models.aihubmix_gemini_model import AihubmixGeminiModel
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import BaseTokenCounter, OpenAITokenCounter, api_keys_required


class AihubmixModel(BaseModelBackend):
    r"""AIHUBMIX provider model backend.

    This model acts as a router to different model backends based on the
    model type. It automatically selects the appropriate backend depending
    on the model name prefix.
    
    Args:
        model_type (Union[ModelType, str]): Model type, supported AIHUBMIX
            model names.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into the model. If :obj:`None`,
            :obj:`AihubmixConfig().as_dict()` will be used. 
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with AIHUBMIX. If not provided, it will be retrieved from the
            environment variable :obj:`AIHUBMIX_API_KEY`. (default: :obj:`None`)
        url (Optional[str], optional): The base URL for AIHUBMIX API.
            Defaults to :obj:`https://api.aihubmix.com/v1` or can be set via
            the environment variable :obj:`AIHUBMIX_API_BASE_URL`.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, a default counter will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout for API requests.
            If not provided, it will use the default timeout. (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional keyword arguments passed to the model backend.
    """

    @api_keys_required([("api_key", "AIHUBMIX_API_KEY")])
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = AihubmixConfig().as_dict()
        super().__init__(model_type, model_config_dict)

        api_key = api_key or os.environ.get("AIHUBMIX_API_KEY")
        model_name = str(self.model_type)

        common_args = {
            "model_type": self.model_type,
            "model_config_dict": self.model_config_dict,
            "api_key": api_key,
            "token_counter": token_counter,
            "timeout": timeout,
            "max_retries": max_retries,
            **kwargs,
        }

        # Route to appropriate backend based on model name
        if model_name.startswith("claude"):
            base_url = url or os.environ.get(
                "AIHUBMIX_API_BASE_URL", "https://api.aihubmix.com/v1"
            )
            self.model_backend: Union[
                AnthropicModel, GeminiModel, OpenAICompatibleModel, AihubmixGeminiModel
            ] = AnthropicModel(url=base_url, **common_args)
        elif (
            model_name.startswith("gemini")
            or model_name.startswith("imagen")
        ) and not model_name.endswith(
            ("-nothink", "-search")
        ) and "embedding" not in model_name:
            # Use the specialized AihubmixGeminiModel for AIHUBMIX Gemini models
            # For AIHUBMIX Gemini models, we should use the specific endpoint
            gemini_url = "https://aihubmix.com/gemini"
            self.model_backend = AihubmixGeminiModel(
                url=gemini_url, **common_args
            )
        else:
            base_url = url or os.environ.get(
                "AIHUBMIX_API_BASE_URL", "https://api.aihubmix.com/v1"
            )
            self.model_backend = OpenAICompatibleModel(
                url=base_url, **common_args
            )

    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Run the model with the given messages.
        
        Args:
            messages (List[OpenAIMessage]): List of messages to send to the model.
            response_format (Optional[Type[BaseModel]], optional): Expected
                response format. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]], optional): List of tools to
                use. (default: :obj:`None`)
                
        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]: Model response.
        """
        return self.model_backend._run(
            messages=messages, response_format=response_format, tools=tools
        )

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Asynchronously run the model with the given messages.
        
        Args:
            messages (List[OpenAIMessage]): List of messages to send to the model.
            response_format (Optional[Type[BaseModel]], optional): Expected
                response format. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]], optional): List of tools to
                use. (default: :obj:`None`)
                
        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]: Model response.
        """
        return await self.model_backend._arun(
            messages=messages, response_format=response_format, tools=tools
        )

    def run(
        self,
        messages: List[Dict],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Run the model with the given messages (dict format).
        
        Args:
            messages (List[Dict]): List of messages to send to the model.
            response_format (Optional[Type[BaseModel]], optional): Expected
                response format. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]], optional): List of tools to
                use. (default: :obj:`None`)
                
        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]: Model response.
        """
        return self.model_backend.run(
            messages=messages, response_format=response_format, tools=tools
        )

    async def arun(
        self,
        messages: List[Dict],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Asynchronously run the model with the given messages (dict format).
        
        Args:
            messages (List[Dict]): List of messages to send to the model.
            response_format (Optional[Type[BaseModel]], optional): Expected
                response format. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]], optional): List of tools to
                use. (default: :obj:`None`)
                
        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]: Model response.
        """
        return await self.model_backend.arun(
            messages=messages, response_format=response_format, tools=tools
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Returns the token counter used by the model backend.
        
        Returns:
            BaseTokenCounter: The token counter.
        """
        return self.model_backend.token_counter

    def check_api_key_or_fail(self) -> None:
        r"""Check if the API key is valid or fail.
        
        Raises:
            ValueError: If the API key is not set or invalid.
        """
        # Fix: Check if the model_backend has the check_api_key_or_fail method before calling it
        if hasattr(self.model_backend, 'check_api_key_or_fail'):
            self.model_backend.check_api_key_or_fail()
