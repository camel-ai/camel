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
"""Faithful asynchronous OpenAI-compatible backend for TITO rollouts."""

from __future__ import annotations

import copy
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Type, Union

from openai import AsyncOpenAI, AsyncStream, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel

from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter


class BaseChatModel(BaseModelBackend):
    """Call an OpenAI-compatible training endpoint without rewriting data.

    Both injected clients and URL-created ``AsyncOpenAI`` clients use
    ``client.chat.completions.create(...)``. The backend is async-only,
    non-streaming, and leaves message history and response content unchanged.

    Examples:
        ``BaseChatModel(url="http://trainer:8000")`` creates ``AsyncOpenAI``;
        ``BaseChatModel(client=test_client)`` injects a compatible client.
    """

    _OPENAI_CREATE_PARAMS: ClassVar[frozenset[str]] = frozenset(
        {
            "audio",
            "frequency_penalty",
            "function_call",
            "functions",
            "logit_bias",
            "logprobs",
            "max_completion_tokens",
            "max_tokens",
            "metadata",
            "modalities",
            "n",
            "parallel_tool_calls",
            "prediction",
            "presence_penalty",
            "prompt_cache_key",
            "reasoning_effort",
            "response_format",
            "safety_identifier",
            "seed",
            "service_tier",
            "stop",
            "store",
            "stream_options",
            "temperature",
            "tool_choice",
            "top_logprobs",
            "top_p",
            "user",
            "verbosity",
            "web_search_options",
            "extra_headers",
            "extra_query",
            "timeout",
        }
    )

    def __init__(
        self,
        model_type: Union[ModelType, str] = "Qwen/Qwen3-0.6B",
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        http_client: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize an injected or URL-backed async model client.

        ``client``/``async_client`` must expose ``chat.completions.create``.
        Otherwise ``url`` creates an owned ``AsyncOpenAI`` client. Client and
        URL inputs are mutually exclusive.
        """
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict or {},
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            # Preserve raw assistant text and response extensions for training.
            extract_thinking_from_response=False,
        )
        if client is not None and async_client is not None:
            raise ValueError("Pass only one of client or async_client")
        if url is not None and (
            client is not None or async_client is not None
        ):
            raise ValueError("Pass either a client or url, not both")
        injected_client = async_client or client
        if injected_client is not None and http_client is not None:
            raise ValueError(
                "http_client cannot be combined with an injected client"
            )

        self._owns_async_client = injected_client is None
        if injected_client is not None:
            self._async_client = injected_client
        else:
            if not url:
                raise ValueError(
                    "url is required when an AsyncOpenAI client is not "
                    "provided"
                )
            client_kwargs = dict(kwargs)
            if http_client is not None:
                client_kwargs["http_client"] = http_client
            self._async_client = AsyncOpenAI(
                api_key=api_key or "Set-but-ignored",
                base_url=self._openai_base_url(url),
                timeout=float(timeout or 180),
                max_retries=max_retries,
                **client_kwargs,
            )

        self._last_prompt_token_ids: List[int] = []
        self._last_output_token_ids: List[int] = []

    @staticmethod
    def _openai_base_url(url: str) -> str:
        """Normalize a URL for use as an ``AsyncOpenAI`` base URL.

        For example, ``http://host:8000`` becomes ``http://host:8000/v1``;
        existing ``/v1`` bases are preserved.
        """
        url = url.rstrip("/")
        if url.endswith("/v1/chat/completions"):
            return url[: -len("/chat/completions")]
        if url.endswith("/v1"):
            return url
        return f"{url}/v1"

    @property
    def token_counter(self) -> BaseTokenCounter:
        """Return a local token counter when one is available.

        The configured counter takes precedence over a client-provided one.
        """
        counter = self._token_counter
        if counter is None:
            counter = getattr(self._async_client, "token_counter", None)
        if counter is None:
            raise RuntimeError(
                "BaseChatModel requires an explicit token_counter when local "
                "token counting is needed"
            )
        return counter

    @property
    def token_limit(self) -> int:
        """Return the context limit used by the append-only agent.

        Resolution order is configured ``context_length``, client tokenizer
        limit, then ``32768``.
        """
        configured = self.model_config_dict.get("context_length")
        if configured is not None:
            return int(configured)
        tokenizer = getattr(self._async_client, "tokenizer", None)
        value = int(getattr(tokenizer, "model_max_length", 32768))
        return value if value < 10**9 else 32768

    def preprocess_messages(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        """Return messages unchanged, without rendering or role conversion."""
        return messages

    def postprocess_response(self, response: Any) -> Any:
        """Preserve assistant content, tool calls, and response metadata."""
        return response

    def _request_config(
        self,
        tools: Optional[List[Dict[str, Any]]],
        response_format: Optional[Type[BaseModel]],
    ) -> Dict[str, Any]:
        """Build one non-streaming OpenAI chat-completion configuration.

        Standard parameters stay as client arguments; framework-specific ones
        move to ``extra_body``. Training aliases are normalized and streaming
        is rejected because the agent requires complete responses.
        """
        config = copy.deepcopy(self.model_config_dict)
        config.pop("context_length", None)
        config.pop("model", None)
        config.pop("messages", None)
        config.pop("tools", None)
        if config.pop("stream", False):
            raise NotImplementedError(
                "BaseChatModel only supports non-streaming rollouts"
            )

        aliases = {
            "max_new_tokens": "max_tokens",
            "min_new_tokens": "min_tokens",
            "sampling_seed": "seed",
        }
        for source, target in aliases.items():
            if source in config:
                config.setdefault(target, config.pop(source))

        extra_body = dict(config.pop("extra_body", None) or {})
        for key in list(config):
            if key not in self._OPENAI_CREATE_PARAMS:
                extra_body[key] = config.pop(key)
        if extra_body:
            config["extra_body"] = extra_body
        config["stream"] = False
        if tools is not None:
            config["tools"] = tools
        if response_format is not None:
            config["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_format.__name__,
                    "schema": response_format.model_json_schema(),
                    "strict": True,
                },
            }
        return config

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        AsyncStream[ChatCompletionChunk],
        AsyncChatCompletionStreamManager[BaseModel],
    ]:
        """Run one asynchronous call through the shared client interface.

        The same path serves injected and URL-created clients; optional token
        IDs are recorded without changing the returned completion.
        """
        response = await self._async_client.chat.completions.create(
            messages=messages,
            model=str(self.model_type),
            **self._request_config(tools, response_format),
        )
        if not isinstance(response, ChatCompletion):
            raise TypeError(
                "BaseChatModel expected a non-streaming ChatCompletion"
            )
        self._record_token_ids(response)
        return response

    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        Stream[ChatCompletionChunk],
        ChatCompletionStreamManager[BaseModel],
    ]:
        """Reject synchronous inference; callers must use :meth:`arun`."""
        raise NotImplementedError("BaseChatModel is asynchronous; use arun()")

    @staticmethod
    def _first_choice(raw: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return the first mapping-shaped choice, or an empty mapping."""
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            return {}
        choice = choices[0]
        return choice if isinstance(choice, Mapping) else {}

    def _record_token_ids(self, response: ChatCompletion) -> None:
        """Retain optional token-ID extensions from a completion.

        IDs may be top-level, choice-level, or contained in SGLang-compatible
        ``meta_info.output_token_logprobs`` entries.
        """
        raw = response.model_dump()
        choice = self._first_choice(raw)
        prompt_ids = raw.get("prompt_token_ids")
        if prompt_ids is None:
            prompt_ids = choice.get("prompt_token_ids")
        self._last_prompt_token_ids = (
            [int(token_id) for token_id in prompt_ids]
            if isinstance(prompt_ids, list)
            else []
        )

        output_ids = raw.get("output_token_ids")
        if output_ids is None:
            output_ids = choice.get("output_token_ids")
        self._last_output_token_ids = (
            [int(token_id) for token_id in output_ids]
            if isinstance(output_ids, list)
            else []
        )
        if self._last_output_token_ids:
            return

        meta_info = choice.get("meta_info")
        logprobs = (
            meta_info.get("output_token_logprobs")
            if isinstance(meta_info, Mapping)
            else None
        )
        if isinstance(logprobs, list):
            for item in logprobs:
                if isinstance(item, (list, tuple)) and len(item) > 1:
                    self._last_output_token_ids.append(int(item[1]))
                elif isinstance(item, Mapping) and "token_id" in item:
                    self._last_output_token_ids.append(int(item["token_id"]))

    @property
    def last_prompt_tokens(self) -> Optional[int]:
        """Return the last exact prompt length, if the client exposed IDs.

        Prefer the in-house client's trajectory, then cached response fields.
        """
        generation = getattr(self._async_client, "last_generation", None)
        if generation is not None:
            return len(generation.prompt_token_ids)
        return (
            len(self._last_prompt_token_ids)
            if self._last_prompt_token_ids
            else None
        )

    @property
    def last_context_tokens(self) -> Optional[int]:
        """Return exact prompt plus output length when token IDs are known."""
        generation = getattr(self._async_client, "last_generation", None)
        if generation is not None:
            return len(generation.prompt_token_ids) + len(
                generation.output_token_ids
            )
        if not self._last_prompt_token_ids:
            return None
        return len(self._last_prompt_token_ids) + len(
            self._last_output_token_ids
        )

    @property
    def last_output_token_ids(self) -> Optional[List[int]]:
        """Return a defensive copy of the last output token IDs, if known."""
        generation = getattr(self._async_client, "last_generation", None)
        if generation is not None:
            return list(generation.output_token_ids)
        return (
            list(self._last_output_token_ids)
            if self._last_output_token_ids
            else None
        )

    async def aclose(self) -> None:
        """Close a URL-created client; injected clients remain caller-owned."""
        if self._owns_async_client:
            async_client = self._async_client
            if async_client is not None:
                await async_client.close()


__all__ = ["BaseChatModel"]
