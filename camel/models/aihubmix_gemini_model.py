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
import uuid
from typing import Any, Dict, List, Optional, Sequence, Type, Union, cast

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import GeminiConfig
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    Choice,
    ModelType,
)
from camel.utils import BaseTokenCounter, api_keys_required

if os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true":
    try:
        from langfuse.decorators import observe
    except ImportError:
        from camel.utils import observe
elif os.environ.get("TRACEROOT_ENABLED", "False").lower() == "true":
    try:
        from traceroot import trace as observe  # type: ignore[import]
    except ImportError:
        from camel.utils import observe
else:
    from camel.utils import observe


class AihubmixGeminiModel(BaseModelBackend):
    r"""AIHUBMIX Gemini API model using Google's native SDK.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of AIHUBMIX Gemini series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`google.genai.types.GenerateContentConfig`.
            If :obj:`None`, :obj:`GeminiConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the AIHUBMIX service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the AIHUBMIX service.
            (default: :obj:`https://aihubmix.com/gemini`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required(
        [
            ("api_key", 'AIHUBMIX_API_KEY'),
        ]
    )
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
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict or GeminiConfig().as_dict(),
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
        )
        
        self.api_key = api_key or os.environ.get("AIHUBMIX_API_KEY")
        self.url = url or os.environ.get(
            "GEMINI_API_BASE_URL", "https://aihubmix.com/gemini"
        )
        self.timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        
        # Initialize the Google genai client
        try:
            from google import genai
            self._client = genai.Client(
                api_key=self.api_key,
                http_options={"base_url": self.url},
            )
        except ImportError:
            raise ImportError(
                "Please install google-genai package to use AihubmixGeminiModel: "
                "pip install google-genai"
            )

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of AIHUBMIX Gemini chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        from google.genai import types
        from google.genai.types import Content, Part
        
        # Convert OpenAI messages to Google genai format
        contents: List[Content] = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Convert role mapping to AIHUBMIX supported roles
            # AIHUBMIX only supports "user" and "model" roles
            if role == 'assistant':
                role_str = 'model'
            elif role != 'user':
                # Default to user role for any other roles (system, etc.)
                role_str = 'user'
            else:
                role_str = 'user'
            
            # Fix 1: Use string literals directly for role
            # The Content constructor accepts string literals
            contents.append(
                Content(
                    role=role_str,  # Use string literal directly
                    parts=[Part.from_text(text=str(content))]
                )
            )
        
        # Prepare generation config - filter out parameters not supported by GenerateContentConfig
        # Common unsupported parameters: n, stream
        supported_params = self.model_config_dict.copy()
        # Remove unsupported parameters for Google's GenerateContentConfig
        unsupported_params = ['n', 'stream']
        for param in unsupported_params:
            supported_params.pop(param, None)
        
        generation_config = types.GenerateContentConfig(
            **supported_params
        )
        
        # Make the API call
        # Fix: Convert contents to the expected format for generate_content
        # The API expects a more flexible type, so we'll cast it properly
        response = self._client.models.generate_content(
            model=self.model_type,
            contents=cast(Any, contents),  # Fix 2: Cast to Any to handle type variance
            config=generation_config,
        )
        
        # Convert response to OpenAI format
        # This is a simplified conversion - in a real implementation,
        # you would need to handle all the fields properly
        # Fix 3: Handle possible None values and properly construct the response
        candidate_content = response.candidates[0].content if response.candidates else None
        content_text = ""
        if candidate_content and candidate_content.parts:
            content_text = str(candidate_content.parts[0].text) if candidate_content.parts[0] else ""
            
        # Create proper Choice object for ChatCompletion
        from openai.types.chat.chat_completion_message import ChatCompletionMessage
        
        choice = Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant",
                content=content_text,
            ),
            finish_reason="stop"
        )
        
        chat_completion = ChatCompletion(
            id=f"aihubmix-gemini-{uuid.uuid4().hex[:8]}",
            choices=[choice],
            created=int(uuid.uuid4().int >> 64),
            model=self.model_type,
            object="chat.completion",
        )
        
        return chat_completion

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of AIHUBMIX Gemini chat completion asynchronously.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """
        # For simplicity, we're calling the sync version in async context
        # In a real implementation, you would use the async client methods
        return self._run(messages, response_format, tools)

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
        # Convert Dict to OpenAIMessage properly
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', ''),
            })
        return self._run(openai_messages, response_format, tools)

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
        # Convert Dict to OpenAIMessage properly
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', ''),
            })
        return await self._arun(openai_messages, response_format, tools)

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Returns the token counter used by the model.
        
        Returns:
            BaseTokenCounter: The token counter.
        """
        # Return a default token counter - in a real implementation,
        # you would use a proper token counter for Gemini models
        if self._token_counter is None:
            from camel.utils import OpenAITokenCounter
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def check_api_key_or_fail(self) -> None:
        r"""Check if the API key is valid or fail.
        
        Raises:
            ValueError: If the API key is not set or invalid.
        """
        if not self.api_key:
            raise ValueError("AIHUBMIX API key is required for AihubmixGeminiModel")
