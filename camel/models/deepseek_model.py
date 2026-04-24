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
from typing import Any, Dict, List, Optional, Type, Union

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

DEEPSEEK_THINKING_MODE_MODELS = {
    "deepseek-reasoner",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
}

DEEPSEEK_THINKING_MODE_ERROR_PARAMS = [
    "logprobs",
    "top_logprobs",
]

DEFAULT_REASONING_SESSION_ID = "__default__"


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
        self._tool_call_reasoning_by_session: Dict[str, Dict[str, str]] = {}
        self._assistant_reasoning_by_session: Dict[str, Dict[str, str]] = {}

    def _get_reasoning_session_id(self) -> str:
        r"""Get the current agent session ID for reasoning cache isolation."""
        try:
            from camel.utils.agent_context import get_current_agent_id

            return get_current_agent_id() or DEFAULT_REASONING_SESSION_ID
        except Exception:
            return DEFAULT_REASONING_SESSION_ID

    @staticmethod
    def _get_tool_call_id(tool_call: Any) -> Optional[str]:
        if isinstance(tool_call, dict):
            tool_call_id = tool_call.get("id")
        else:
            tool_call_id = getattr(tool_call, "id", None)

        return tool_call_id if isinstance(tool_call_id, str) else None

    @staticmethod
    def _get_message_content(message: Any) -> Optional[str]:
        if isinstance(message, dict):
            content = message.get("content")
        else:
            content = getattr(message, "content", None)

        return content if isinstance(content, str) else None

    def _cache_tool_call_reasoning(self, response: Any) -> None:
        r"""Cache reasoning content for DeepSeek thinking-mode tool calls.

        DeepSeek requires the assistant ``reasoning_content`` generated with a
        tool call to be passed back in later requests. CAMEL memory stores the
        OpenAI-compatible tool-call message, so the model layer keeps the
        DeepSeek-specific field keyed by tool_call_id and injects it before
        the next request.
        """
        if not isinstance(response, ChatCompletion):
            return

        session_id = self._get_reasoning_session_id()
        session_cache = self._tool_call_reasoning_by_session.setdefault(
            session_id, {}
        )
        assistant_reasoning_cache = (
            self._assistant_reasoning_by_session.setdefault(session_id, {})
        )

        for choice in response.choices:
            message = getattr(choice, "message", None)
            if message is None:
                continue

            reasoning_content = getattr(message, "reasoning_content", None)
            content = self._get_message_content(message)
            if reasoning_content and content:
                assistant_reasoning_cache[content] = reasoning_content

            tool_calls = getattr(message, "tool_calls", None)
            if not reasoning_content or not tool_calls:
                continue

            for tool_call in tool_calls:
                tool_call_id = self._get_tool_call_id(tool_call)
                if tool_call_id:
                    session_cache[tool_call_id] = reasoning_content

    def _inject_tool_call_reasoning(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""Inject cached reasoning into assistant tool-call messages."""
        session_cache = self._tool_call_reasoning_by_session.get(
            self._get_reasoning_session_id(), {}
        )
        assistant_reasoning_cache = self._assistant_reasoning_by_session.get(
            self._get_reasoning_session_id(), {}
        )
        if not session_cache:
            return messages

        processed_messages: List[OpenAIMessage] = []
        for message in messages:
            if (
                isinstance(message, dict)
                and message.get("role") == "assistant"
                and message.get("tool_calls")
                and not message.get("reasoning_content")
            ):
                reasoning_content = None
                tool_calls = message.get("tool_calls") or []
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        tool_call_id = self._get_tool_call_id(tool_call)
                        if tool_call_id and tool_call_id in session_cache:
                            reasoning_content = session_cache[tool_call_id]
                            break

                if reasoning_content:
                    message = dict(message)
                    message["reasoning_content"] = reasoning_content
            elif (
                isinstance(message, dict)
                and message.get("role") == "assistant"
                and not message.get("reasoning_content")
            ):
                content = self._get_message_content(message)
                if content and content in assistant_reasoning_cache:
                    message = dict(message)
                    message["reasoning_content"] = assistant_reasoning_cache[
                        content
                    ]

            processed_messages.append(message)

        return processed_messages

    def preprocess_messages(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""Preprocess messages and restore DeepSeek tool-call reasoning."""
        messages = super().preprocess_messages(messages)
        return self._inject_tool_call_reasoning(messages)

    def postprocess_response(self, response: Any) -> Any:
        r"""Postprocess responses and cache DeepSeek tool-call reasoning."""
        response = super().postprocess_response(response)
        self._cache_tool_call_reasoning(response)
        return response

    def _normalize_thinking_config(
        self, request_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Move top-level ``thinking`` into ``extra_body`` for OpenAI SDK."""
        thinking = request_config.pop("thinking", None)
        if thinking is None:
            return request_config

        extra_body = request_config.get("extra_body") or {}
        if not isinstance(extra_body, dict):
            raise ValueError("DeepSeek `extra_body` must be a dictionary.")

        extra_body = copy.deepcopy(extra_body)
        extra_body["thinking"] = thinking
        request_config["extra_body"] = extra_body
        return request_config

    def _is_thinking_mode_enabled(
        self, request_config: Dict[str, Any]
    ) -> bool:
        extra_body = request_config.get("extra_body") or {}
        thinking = None
        if isinstance(extra_body, dict):
            thinking = extra_body.get("thinking")

        if isinstance(thinking, dict):
            thinking_type = thinking.get("type")
            if thinking_type == "disabled":
                return False
            if thinking_type == "enabled":
                return True

        return str(self.model_type) in DEEPSEEK_THINKING_MODE_MODELS

    def _prepare_request(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        request_config = copy.deepcopy(self.model_config_dict)
        request_config = self._normalize_thinking_config(request_config)

        if self._is_thinking_mode_enabled(request_config):
            for param in DEEPSEEK_THINKING_MODE_ERROR_PARAMS:
                if param in request_config:
                    logger.warning(
                        "`%s` is not supported by DeepSeek thinking mode "
                        "and will be ignored.",
                        param,
                    )
                    request_config.pop(param, None)

        # Remove strict from each tool's function parameters since DeepSeek
        # does not support them
        if tools:
            tools = copy.deepcopy(tools)
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

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        self._log_and_trace()

        request_config = self._prepare_request(
            messages, response_format, tools
        )

        response = self._call_client(
            self._client.chat.completions.create,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

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

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """
        self._log_and_trace()

        request_config = self._prepare_request(
            messages, response_format, tools
        )
        response = await self._acall_client(
            self._async_client.chat.completions.create,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

        return response
