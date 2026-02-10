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

import copy
import os
from typing import Any, Dict, List, Optional, Type, Union, cast

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import DeepSeekConfig
from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models._utils import try_modify_message_with_format
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)

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


logger = get_logger(__name__)

REASONSER_UNSUPPORTED_PARAMS = [
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "logprobs",
    "top_logprobs",
]


class DeepSeekModel(OpenAICompatibleModel):
    r"""DeepSeek API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`DeepSeekConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the DeepSeek service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the DeepSeek service.
            (default: :obj:`https://api.deepseek.com`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.

    References:
        https://api-docs.deepseek.com/
    """

    @api_keys_required(
        [
            ("api_key", "DEEPSEEK_API_KEY"),
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
        if model_config_dict is None:
            model_config_dict = DeepSeekConfig().as_dict()
        api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        url = url or os.environ.get(
            "DEEPSEEK_API_BASE_URL",
            "https://api.deepseek.com",
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
        # Map tool_call_id -> reasoning_content for multi-turn tool calls.
        # Since ChatAgent memory doesn't store reasoning_content, we need to
        # keep all of them and re-inject on every request within the same turn.
        # Cleared at the start of a new turn (new user message).
        self._reasoning_content_map: Dict[str, str] = {}

    def _is_thinking_enabled(self) -> bool:
        r"""Check if thinking (reasoning) mode is enabled.

        Returns:
            bool: Whether thinking mode is enabled.
        """
        if self.model_type in [ModelType.DEEPSEEK_REASONER]:
            return True
        thinking = self.model_config_dict.get("thinking")
        return isinstance(thinking, dict) and thinking.get("type") == "enabled"

    def _inject_reasoning_content(
        self,
        messages: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        r"""Inject reasoning_content into all assistant messages that need it.

        Args:
            messages: The original messages list.

        Returns:
            Messages with reasoning_content injected where needed.
        """
        if not messages:
            return messages

        # New turn (last message is user) -> clear map and return as-is
        last_msg = messages[-1]
        if isinstance(last_msg, dict) and last_msg.get("role") == "user":
            self._reasoning_content_map.clear()
            return messages

        if not self._reasoning_content_map:
            return messages

        # Inject reasoning_content into ALL assistant messages that need it
        processed: List[OpenAIMessage] = []
        for msg in messages:
            if (
                isinstance(msg, dict)
                and msg.get("role") == "assistant"
                and msg.get("tool_calls")
                and "reasoning_content" not in msg
            ):
                tool_calls = cast(
                    List[Dict[str, Any]], msg.get("tool_calls", [])
                )
                if tool_calls:
                    first_id = tool_calls[0].get("id", "")
                    reasoning = self._reasoning_content_map.get(first_id)
                    if reasoning:
                        new_msg = cast(Dict[str, Any], copy.deepcopy(msg))
                        new_msg["reasoning_content"] = reasoning
                        processed.append(cast(OpenAIMessage, new_msg))
                        continue
            processed.append(msg)

        return processed

    def _store_reasoning_content(self, response: ChatCompletion) -> None:
        r"""Store reasoning_content from the model response.

        Args:
            response: The model response.
        """
        if not response.choices:
            return

        message = response.choices[0].message
        reasoning = getattr(message, "reasoning_content", None)
        tool_calls = getattr(message, "tool_calls", None)

        if reasoning and tool_calls:
            for tc in tool_calls:
                tc_id = getattr(tc, "id", None)
                if tc_id:
                    self._reasoning_content_map[tc_id] = reasoning

    def _prepare_request(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        request_config = copy.deepcopy(self.model_config_dict)

        if self.model_type in [
            ModelType.DEEPSEEK_REASONER,
        ]:
            logger.warning(
                "Warning: You are using a DeepSeek Reasoner model, "
                "which has certain limitations, reference: "
                "`https://api-docs.deepseek.com/guides/reasoning_model"
                "#api-parameters`.",
            )
            request_config = {
                key: value
                for key, value in request_config.items()
                if key not in REASONSER_UNSUPPORTED_PARAMS
            }

        thinking = request_config.pop("thinking", None)
        if thinking:
            request_config["extra_body"] = {
                **request_config.get("extra_body", {}),
                "thinking": thinking,
            }

        # Remove strict from each tool's function parameters since DeepSeek
        # does not support them
        if tools:
            for tool in tools:
                function_dict = tool.get('function', {})
                function_dict.pop("strict", None)
            request_config["tools"] = tools
        elif response_format:
            try_modify_message_with_format(messages[-1], response_format)
            request_config["response_format"] = {"type": "json_object"}

        return request_config

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of DeepSeek chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools
                to use for the request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        if self._is_thinking_enabled():
            messages = self._inject_reasoning_content(messages)

        self._log_and_trace()

        request_config = self._prepare_request(
            messages, response_format, tools
        )

        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

        # Store reasoning_content for future requests
        if self._is_thinking_enabled() and isinstance(
            response, ChatCompletion
        ):
            self._store_reasoning_content(response)

        return response

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of DeepSeek chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools
                to use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """
        if self._is_thinking_enabled():
            messages = self._inject_reasoning_content(messages)

        self._log_and_trace()

        request_config = self._prepare_request(
            messages, response_format, tools
        )

        response = await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

        # Store reasoning_content for future requests
        if self._is_thinking_enabled() and isinstance(
            response, ChatCompletion
        ):
            self._store_reasoning_content(response)

        return response
