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
"""OpenAI Responses API backend in a unified BaseModelBackend interface."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

from camel.core.messages import (
    camel_messages_to_responses_request,
    openai_messages_to_camel,
)
from camel.messages import OpenAIMessage
from camel.models._utils import convert_openai_tools_to_responses_format
from camel.models.base_model import BaseModelBackend
from camel.responses.adapters.responses_adapter import (
    async_responses_stream_to_chunks,
    responses_stream_to_chunks,
    responses_to_camel_response,
)
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    get_current_agent_session_id,
    is_langfuse_available,
    update_langfuse_trace,
)


class OpenAIResponsesModel(BaseModelBackend):
    r"""OpenAI Responses API backend returning CamelModelResponse.

    This backend is additive and does not alter existing OpenAIModel logic.
    It accepts OpenAI-style messages for compatibility, converts them to the
    Responses input shape, calls `responses.create`, then maps the provider
    result to `CamelModelResponse`.
    """

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
            model_config_dict = {}
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))

        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter, timeout
        )

        # Create clients (Langfuse-aware when available)
        if is_langfuse_available():
            from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
            from langfuse.openai import OpenAI as LangfuseOpenAI

            self._client = LangfuseOpenAI(
                timeout=self._timeout,
                max_retries=max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )
            self._async_client = LangfuseAsyncOpenAI(
                timeout=self._timeout,
                max_retries=max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )
        else:
            self._client = OpenAI(
                timeout=self._timeout,
                max_retries=max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )
            self._async_client = AsyncOpenAI(
                timeout=self._timeout,
                max_retries=max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )

    @property
    def token_counter(self) -> BaseTokenCounter:
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(self.model_type)
        return self._token_counter

    # ----------------------- BaseModelBackend API -----------------------
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:  # unused legacy types in signature
        # Update trace
        agent_session_id = get_current_agent_session_id()
        if agent_session_id:
            update_langfuse_trace(
                session_id=agent_session_id,
                metadata={
                    "agent_id": str(agent_session_id),
                    "model_type": str(self.model_type),
                },
                tags=["CAMEL-AI", str(self.model_type)],
            )

        # Convert OpenAI chat to Camel messages, then to Responses body
        camel_msgs = openai_messages_to_camel(messages)
        body = camel_messages_to_responses_request(camel_msgs)

        # Merge extra args from model_config_dict
        request_dict = dict(self.model_config_dict)
        is_streaming = bool(request_dict.pop("stream", False))
        request_dict.update(body)

        # Tools: Responses also accepts `tools`; pass through when provided
        if tools:
            request_dict["tools"] = convert_openai_tools_to_responses_format(
                tools
            )

        if is_streaming:
            if response_format is not None:
                raise NotImplementedError(
                    "Responses streaming with response_format is not supported yet."  # noqa:E501
                )
            request_dict["stream"] = True
            stream = self._client.responses.create(
                model=self.model_type, **request_dict
            )
            return responses_stream_to_chunks(stream)  # type: ignore[return-value]

        if response_format is not None:
            # Structured outputs require Responses.parse with text_format
            parse_fn = getattr(self._client.responses, "parse", None)
            if not callable(parse_fn):
                raise RuntimeError(
                    "responses.parse is not available. "
                    "Upgrade the openai package to support Responses.parse, "
                    "or call without response_format."
                )
            try:
                resp = parse_fn(
                    model=self.model_type,
                    text_format=response_format,
                    **request_dict,
                )
            except Exception as e:
                raise RuntimeError(
                    "Failed to perform structured parse via Responses API. "
                    "Check that your model supports structured outputs."
                ) from e
            return responses_to_camel_response(
                resp, expected_parsed_type=response_format
            )  # type: ignore[return-value]
        else:
            resp = self._client.responses.create(
                model=self.model_type, **request_dict
            )
            return responses_to_camel_response(resp)  # type: ignore[return-value]

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        agent_session_id = get_current_agent_session_id()
        if agent_session_id:
            update_langfuse_trace(
                session_id=agent_session_id,
                metadata={
                    "agent_id": str(agent_session_id),
                    "model_type": str(self.model_type),
                },
                tags=["CAMEL-AI", str(self.model_type)],
            )

        camel_msgs = openai_messages_to_camel(messages)
        body = camel_messages_to_responses_request(camel_msgs)
        request_dict = dict(self.model_config_dict)
        is_streaming = bool(request_dict.pop("stream", False))
        request_dict.update(body)
        if tools:
            request_dict["tools"] = convert_openai_tools_to_responses_format(
                tools
            )

        if is_streaming:
            if response_format is not None:
                raise NotImplementedError(
                    "Responses streaming with response_format is not supported yet."  # noqa:E501
                )
            request_dict["stream"] = True
            stream = await self._async_client.responses.create(
                model=self.model_type, **request_dict
            )
            # Use async version for proper async iteration
            return async_responses_stream_to_chunks(stream)  # type: ignore[return-value]

        if response_format is not None:
            parse_fn = getattr(self._async_client.responses, "parse", None)
            if not callable(parse_fn):
                raise RuntimeError(
                    "responses.parse is not available. "
                    "Please upgrade the openai package."
                )
            try:
                resp = await parse_fn(
                    model=self.model_type,
                    text_format=response_format,
                    **request_dict,
                )
            except Exception as e:
                raise RuntimeError(
                    "Failed to call structured parse via Responses API. "
                    "Check model support and SDK version."
                ) from e
            return responses_to_camel_response(
                resp, expected_parsed_type=response_format
            )  # type: ignore[return-value]
        else:
            resp = await self._async_client.responses.create(
                model=self.model_type, **request_dict
            )
            return responses_to_camel_response(resp)  # type: ignore[return-value]
