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
# Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved.
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
from __future__ import annotations

import copy
import os
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)

from openai import AsyncOpenAI, AsyncStream, OpenAI, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from openai.types.chat import ChatCompletionChunk
from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseUsage,
)
from pydantic import BaseModel

from camel.core import (
    CamelMessage,
    CamelModelResponse,
    CamelStreamChunk,
    CamelToolCall,
    CamelToolCallDelta,
    CamelUsage,
)
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import ModelType, UnifiedModelType
from camel.utils import BaseTokenCounter, OpenAITokenCounter, api_keys_required


def _messages_to_response_input(
    messages: Sequence[OpenAIMessage],
) -> List[Dict[str, Any]]:
    r"""Convert ChatCompletion-style messages to Responses API input schema."""
    response_input: List[Dict[str, Any]] = []
    for message in messages:
        message_dict = cast(Dict[str, Any], message)
        role = message_dict.get("role")
        content = message_dict.get("content")
        if isinstance(content, list):
            fragments = []
            for item in content:
                if isinstance(item, dict) and "type" in item:
                    fragments.append(item)
                else:
                    fragments.append({"type": "input_text", "text": str(item)})
        elif content is None:
            fragments = []
        else:
            fragments = [{"type": "input_text", "text": str(content)}]
        response_input.append({"role": role, "content": fragments})
    return response_input


def _response_output_text_to_str(content_items: Sequence[Any]) -> str:
    text_parts: List[str] = []
    for item in content_items:
        if isinstance(item, ResponseOutputText):
            text_parts.append(item.text)
        elif isinstance(item, dict) and item.get("type") == "output_text":
            text_parts.append(str(item.get("text", "")))
    return "".join(text_parts)


def _extract_tool_calls(
    response: Response,
) -> List[CamelToolCall]:
    tool_calls: List[CamelToolCall] = []
    for output_item in response.output or []:
        if isinstance(output_item, ResponseFunctionToolCall):
            tool_calls.append(
                CamelToolCall(
                    name=output_item.name,
                    arguments=output_item.arguments,
                    id=output_item.call_id or output_item.id,
                    type="function",
                    raw=output_item,
                )
            )
        elif isinstance(output_item, dict):
            if output_item.get("type") == "function_call":
                tool_calls.append(
                    CamelToolCall(
                        name=output_item.get("name"),
                        arguments=output_item.get("arguments"),
                        id=output_item.get("call_id") or output_item.get("id"),
                        type="function",
                        raw=output_item,
                    )
                )
    return tool_calls


def _response_usage_to_camel(
    usage: Optional[ResponseUsage],
) -> Optional[CamelUsage]:
    if usage is None:
        return None
    return CamelUsage(
        prompt_tokens=getattr(usage, "input_tokens", None),
        completion_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        raw=usage,
    )


def _response_to_camel(response: Response) -> CamelModelResponse:
    messages: List[CamelMessage] = []

    for output_item in response.output or []:
        if isinstance(output_item, ResponseOutputMessage):
            content_str = _response_output_text_to_str(output_item.content)
            messages.append(
                CamelMessage(
                    role=getattr(output_item, "role", "assistant"),
                    content=content_str,
                    raw=output_item,
                )
            )
        elif (
            isinstance(output_item, dict)
            and output_item.get("type") == "message"
        ):
            content_items = output_item.get("content", [])
            content_str = _response_output_text_to_str(content_items)
            messages.append(
                CamelMessage(
                    role=output_item.get("role", "assistant"),
                    content=content_str,
                    raw=output_item,
                )
            )

    tool_calls = _extract_tool_calls(response)
    if tool_calls and messages:
        # Attach tool calls to the latest assistant message
        messages[-1].tool_calls = tool_calls

    finish_reasons: List[str] = []
    if response.status:
        finish_reasons.append(response.status)
    elif messages:
        finish_reasons.extend(["completed"] * len(messages))

    camel_usage = _response_usage_to_camel(response.usage)

    return CamelModelResponse(
        messages=messages,
        finish_reasons=finish_reasons,
        usage=camel_usage,
        response_id=response.id,
        raw=response,
    )


class OpenAIResponsesModel(BaseModelBackend):
    r"""OpenAI Responses API backend producing CamelModelResponse objects."""

    @api_keys_required(
        [
            ("api_key", "OPENAI_API_KEY"),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str, UnifiedModelType],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        model_type = UnifiedModelType(model_type)
        model_config_dict = model_config_dict or {}
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))

        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
        )

        client_kwargs = dict(
            timeout=self._timeout,
            max_retries=self._max_retries,
            base_url=self._url,
            api_key=self._api_key,
            **kwargs,
        )

        self._client = OpenAI(**client_kwargs)
        self._async_client = AsyncOpenAI(**client_kwargs)

    @property
    def token_counter(self) -> BaseTokenCounter:
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(self.model_type)
        return self._token_counter

    def _sanitize_request_config(
        self, request_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        sanitized = copy.deepcopy(request_config)
        sanitized.pop("stream", None)
        sanitized.pop("functions", None)
        return sanitized

    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        CamelModelResponse,
        Stream[ChatCompletionChunk],
        ChatCompletionStreamManager[BaseModel],
    ]:
        request_config = self._sanitize_request_config(self.model_config_dict)
        if tools is not None:
            request_config["tools"] = tools

        stream_enabled = request_config.pop("stream", False)

        response_input = cast(List[Any], _messages_to_response_input(messages))

        if stream_enabled:
            stream_kwargs = dict(
                model=str(self.model_type),
                input=response_input,
                **request_config,
            )
            if response_format is not None:
                stream_kwargs["text_format"] = response_format

            stream_manager = self._client.responses.stream(  # type: ignore[arg-type]
                **stream_kwargs
            )
            return cast(
                ChatCompletionStreamManager[BaseModel],
                _ResponsesStreamManagerAdapter(
                    stream_manager, response_format
                ),
            )

        if response_format is not None:
            parsed = self._client.responses.parse(  # type: ignore[arg-type]
                model=str(self.model_type),
                input=response_input,
                text_format=response_format,
                **request_config,
            )
            camel_response = _response_to_camel(parsed)
            _apply_structured_parse_result(
                camel_response, response_format, parsed
            )
            return camel_response

        response = self._client.responses.create(  # type: ignore[arg-type]
            model=str(self.model_type),
            input=response_input,
            **request_config,
        )
        camel_response = _response_to_camel(response)
        _apply_structured_parse_result(
            camel_response, response_format, response
        )
        return camel_response

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        CamelModelResponse,
        AsyncStream[ChatCompletionChunk],
        AsyncChatCompletionStreamManager[BaseModel],
    ]:
        request_config = self._sanitize_request_config(self.model_config_dict)
        if tools is not None:
            request_config["tools"] = tools

        stream_enabled = request_config.pop("stream", False)

        response_input = cast(List[Any], _messages_to_response_input(messages))

        if stream_enabled:
            stream_kwargs = dict(
                model=str(self.model_type),
                input=response_input,
                **request_config,
            )
            if response_format is not None:
                stream_kwargs["text_format"] = response_format

            stream_manager = self._async_client.responses.stream(  # type: ignore[arg-type]
                **stream_kwargs
            )
            return cast(
                AsyncChatCompletionStreamManager[BaseModel],
                _AsyncResponsesStreamManagerAdapter(
                    stream_manager, response_format
                ),
            )

        if response_format is not None:
            parsed = await self._async_client.responses.parse(  # type: ignore[arg-type]
                model=str(self.model_type),
                input=response_input,
                text_format=response_format,
                **request_config,
            )
            camel_response = _response_to_camel(parsed)
            _apply_structured_parse_result(
                camel_response, response_format, parsed
            )
            return camel_response

        response = await self._async_client.responses.create(  # type: ignore[arg-type]
            model=str(self.model_type),
            input=response_input,
            **request_config,
        )
        camel_response = _response_to_camel(response)
        _apply_structured_parse_result(
            camel_response, response_format, response
        )
        return camel_response


def _apply_structured_parse_result(
    camel_response: CamelModelResponse,
    response_format: Optional[Type[BaseModel]],
    response: Response,
) -> None:
    if response_format is None or not camel_response.messages:
        return

    parsed_value = getattr(response, "output_parsed", None)
    if parsed_value is not None:
        camel_response.messages[0].parsed = parsed_value
        return

    content = camel_response.messages[0].content
    if isinstance(content, str) and content:
        try:
            camel_response.messages[
                0
            ].parsed = response_format.model_validate_json(content)
        except Exception:
            pass


class _ResponsesStreamAdapterBase:
    def __init__(self, response_format: Optional[Type[BaseModel]]) -> None:
        self._response_format = response_format
        self._completed_response: Optional[Response] = None
        self._function_calls: Dict[str, Dict[str, Any]] = {}

    def _register_function_call(self, item: ResponseFunctionToolCall) -> None:
        call_id = item.call_id or item.id
        if not call_id:
            return
        entry = {
            "id": item.id or call_id,
            "call_id": call_id,
            "name": item.name or "",
            "name_emitted": False,
            "arguments_total": "",
        }
        self._function_calls[call_id] = entry
        if item.id and item.id != call_id:
            self._function_calls[item.id] = entry

    def _handle_event(self, event: Any) -> List[CamelStreamChunk]:
        event_type = getattr(event, "type", None)

        if event_type == "response.output_item.added":
            item = getattr(event, "item", None)
            if isinstance(item, ResponseFunctionToolCall):
                self._register_function_call(item)
            return []

        if event_type == "response.output_text.delta":
            delta_text = getattr(event, "delta", "") or ""
            return [
                CamelStreamChunk(
                    content_delta=str(delta_text),
                    raw=event,
                )
            ]

        if event_type == "response.function_call_arguments.delta":
            entry = self._function_calls.get(getattr(event, "item_id", ""))
            if not entry:
                return []
            delta_text = getattr(event, "delta", "") or ""
            entry["arguments_total"] += delta_text
            if not entry["name_emitted"]:
                name_delta = entry["name"]
                entry["name_emitted"] = True
            else:
                name_delta = ""
            tool_delta = CamelToolCallDelta(
                tool_call_id=entry.get("id")
                or getattr(event, "item_id", None),
                name_delta=name_delta,
                arguments_delta=delta_text,
                raw=event,
            )
            return [
                CamelStreamChunk(
                    tool_call_deltas=[tool_delta],
                    raw=event,
                )
            ]

        if event_type == "response.completed":
            self._completed_response = getattr(event, "response", None)
            finish_chunk = CamelStreamChunk(
                finish_reason="stop",
                raw=event,
            )
            usage = (
                getattr(event.response, "usage", None)
                if self._completed_response
                else None
            )
            if usage is not None:
                finish_chunk.usage = _response_usage_to_camel(usage)
            return [finish_chunk]

        if event_type in {"response.error", "response.failed"}:
            error_obj = getattr(event, "error", None)
            message = getattr(error_obj, "message", "Responses stream error")
            raise RuntimeError(message)

        return []

    def _final_camel_response(self, response: Response) -> CamelModelResponse:
        camel_response = _response_to_camel(response)
        _apply_structured_parse_result(
            camel_response, self._response_format, response
        )
        return camel_response


class _ResponsesStreamAdapter(_ResponsesStreamAdapterBase):
    def __init__(
        self, stream: Any, response_format: Optional[Type[BaseModel]]
    ) -> None:
        super().__init__(response_format)
        self._stream = stream

    def __iter__(self) -> Iterator[CamelStreamChunk]:
        for event in self._stream:
            for chunk in self._handle_event(event):
                yield chunk

    def get_final_completion(self) -> CamelModelResponse:
        if self._completed_response is None:
            parsed_response = self._stream.get_final_response()
            self._completed_response = parsed_response
        if self._completed_response is None:
            raise RuntimeError("No completion received from Responses stream.")
        return self._final_camel_response(self._completed_response)


class _ResponsesStreamManagerAdapter(
    ContextManager[Iterator[CamelStreamChunk]]
):
    def __init__(
        self,
        manager: Any,
        response_format: Optional[Type[BaseModel]],
    ) -> None:
        self._manager = manager
        self._response_format = response_format
        self._adapter: Optional[_ResponsesStreamAdapter] = None

    def __enter__(self) -> Iterator[CamelStreamChunk]:
        stream = self._manager.__enter__()
        self._adapter = _ResponsesStreamAdapter(stream, self._response_format)
        return self._adapter

    def __exit__(
        self,
        exc_type,
        exc,
        exc_tb,
    ) -> Optional[bool]:
        return self._manager.__exit__(exc_type, exc, exc_tb)


class _AsyncResponsesStreamAdapter(_ResponsesStreamAdapterBase):
    def __init__(
        self, stream: Any, response_format: Optional[Type[BaseModel]]
    ) -> None:
        super().__init__(response_format)
        self._stream = stream

    async def __aiter__(self) -> AsyncIterator[CamelStreamChunk]:
        async for event in self._stream:
            for chunk in self._handle_event(event):
                yield chunk

    async def get_final_completion(self) -> CamelModelResponse:
        if self._completed_response is None:
            parsed_response = await self._stream.get_final_response()
            self._completed_response = parsed_response
        if self._completed_response is None:
            raise RuntimeError("No completion received from Responses stream.")
        return self._final_camel_response(self._completed_response)


class _AsyncResponsesStreamManagerAdapter(
    AsyncContextManager[AsyncIterator[CamelStreamChunk]]
):
    def __init__(
        self,
        manager: Any,
        response_format: Optional[Type[BaseModel]],
    ) -> None:
        self._manager = manager
        self._response_format = response_format
        self._adapter: Optional[_AsyncResponsesStreamAdapter] = None

    async def __aenter__(self) -> AsyncIterator[CamelStreamChunk]:
        stream = await self._manager.__aenter__()
        self._adapter = _AsyncResponsesStreamAdapter(
            stream, self._response_format
        )
        return self._adapter

    async def __aexit__(
        self,
        exc_type,
        exc,
        exc_tb,
    ) -> Optional[bool]:
        return await self._manager.__aexit__(exc_type, exc, exc_tb)
