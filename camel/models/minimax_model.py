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
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import MinimaxConfig
from camel.messages import OpenAIMessage
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)


class MinimaxModel(OpenAICompatibleModel):
    r"""LLM API served by Minimax in a unified OpenAICompatibleModel
    interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`.
            If:obj:`None`, :obj:`MinimaxConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the Minimax service. (default: :obj:`None`).
        url (Optional[str], optional): The url to the Minimax M2 service.
            (default: :obj:`None`)
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

    @api_keys_required([("api_key", "MINIMAX_API_KEY")])
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
            model_config_dict = MinimaxConfig().as_dict()
        api_key = api_key or os.environ.get("MINIMAX_API_KEY")
        url = url or os.environ.get(
            "MINIMAX_API_BASE_URL", "https://api.minimaxi.com/v1"
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )
        # Store the last reasoning_details from model response for
        # interleaved thinking support (MiniMax M2 models)
        self._last_reasoning_details: Optional[Any] = None

    def _is_thinking_enabled(self) -> bool:
        r"""Check if interleaved thinking mode is enabled.

        Returns:
            bool: True if interleaved_thinking is enabled in the model config.
        """
        return bool(self.model_config_dict.get("interleaved_thinking", False))

    def _prepare_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Prepare the request configuration dictionary.

        Overrides the base method to:
        1. Remove interleaved_thinking parameter (internal use only)
        2. Add reasoning_split=True to extra_body when thinking is enabled
        """
        request_config = super()._prepare_request_config(tools)
        request_config.pop("interleaved_thinking", None)

        # Add reasoning_split to extra_body when interleaved thinking is
        # enabled
        if self._is_thinking_enabled():
            extra_body = request_config.get("extra_body", {})
            extra_body["reasoning_split"] = True
            request_config["extra_body"] = extra_body

        return request_config

    def _inject_reasoning_details(
        self,
        messages: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        r"""Inject the last reasoning_details into assistant messages.

        For MiniMax M2 models with interleaved thinking enabled,
        the reasoning_details from the model response needs to be passed back
        in subsequent requests for proper context management.

        Args:
            messages: The original messages list.

        Returns:
            Messages with reasoning_details added to the last assistant
            message that has tool_calls.
        """
        if not self._last_reasoning_details or not self._is_thinking_enabled():
            return messages

        # Find the last assistant message with tool_calls and inject
        # reasoning_details
        processed: List[OpenAIMessage] = []
        reasoning_injected = False

        for msg in reversed(messages):
            if (
                not reasoning_injected
                and isinstance(msg, dict)
                and msg.get("role") == "assistant"
                and msg.get("tool_calls")
                and "reasoning_details" not in msg
            ):
                # Inject reasoning_details into this message
                new_msg = dict(msg)
                new_msg["reasoning_details"] = self._last_reasoning_details
                processed.append(new_msg)  # type: ignore[arg-type]
                reasoning_injected = True
            else:
                processed.append(msg)

        # Only clear after successful injection
        if reasoning_injected:
            self._last_reasoning_details = None

        return list(reversed(processed))

    def _extract_reasoning_details(
        self, response: ChatCompletion
    ) -> Optional[Any]:
        r"""Extract reasoning_details from the model response.

        Args:
            response: The model response.

        Returns:
            The reasoning_details if available, None otherwise.
        """
        if response.choices:
            return getattr(
                response.choices[0].message, "reasoning_details", None
            )
        return None

    def run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of MiniMax chat completion.

        Overrides the base run method to inject reasoning_details from
        previous responses into subsequent requests, as required by
        MiniMax M2 models with interleaved thinking enabled.

        Args:
            messages: Message list with the chat history in OpenAI API format.
            response_format: The format of the response.
            tools: The schema of the tools to use for the request.

        Returns:
            ChatCompletion in the non-stream mode, or
            Stream[ChatCompletionChunk] in the stream mode.
        """
        # Inject reasoning_details from previous response if thinking is
        # enabled
        processed_messages = self._inject_reasoning_details(messages)

        # Call parent's run
        response = super().run(processed_messages, response_format, tools)

        # Extract and store reasoning_details for next request
        if isinstance(response, ChatCompletion):
            self._last_reasoning_details = self._extract_reasoning_details(
                response
            )

        return response

    async def arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs async inference of MiniMax chat completion.

        Overrides the base arun method to inject reasoning_details from
        previous responses into subsequent requests, as required by
        MiniMax M2 models with interleaved thinking enabled.

        Args:
            messages: Message list with the chat history in OpenAI API format.
            response_format: The format of the response.
            tools: The schema of the tools to use for the request.

        Returns:
            ChatCompletion in the non-stream mode, or
            AsyncStream[ChatCompletionChunk] in the stream mode.
        """
        # Inject reasoning_details from previous response if thinking is
        # enabled
        processed_messages = self._inject_reasoning_details(messages)

        # Call parent's arun
        response = await super().arun(
            processed_messages, response_format, tools
        )

        # Extract and store reasoning_details for next request
        if isinstance(response, ChatCompletion):
            self._last_reasoning_details = self._extract_reasoning_details(
                response
            )

        return response
