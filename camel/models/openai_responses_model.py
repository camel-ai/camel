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
from camel.models.base_model import BaseModelBackend
from camel.responses.model_response import CamelModelResponse
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

    # ----------------------- helpers -----------------------
    def _to_camel_response_from_responses(
        self, resp: Any, expected_parsed_type: Optional[Type[BaseModel]] = None
    ) -> CamelModelResponse:
        """Map a minimal Responses object to CamelModelResponse.

        This uses duck typing to avoid hard dependencies on a specific
        provider SDK version. It handles the common `output_text` and
        aggregates text from `output[].content[]` as a fallback.
        """
        text = getattr(resp, "output_text", None)
        if not text:
            # Fallback: concatenate all text parts from output[].content[]
            parts: List[str] = []
            output = getattr(resp, "output", None)
            if isinstance(output, list):
                for item in output:
                    content = getattr(item, "content", None) or (
                        item.get("content") if isinstance(item, dict) else None
                    )
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in (
                                "output_text",
                                "text",
                                "input_text",
                            ):
                                val = (
                                    c.get("text") or c.get("output_text") or ""
                                )
                                if val:
                                    parts.append(str(val))
            text = "\n".join(parts) if parts else ""

        from camel.messages.base import BaseMessage
        from camel.types import RoleType

        parsed_obj = None
        if expected_parsed_type is not None:
            # Prefer SDK's top-level parsed field
            parsed_obj = getattr(resp, "output_parsed", None)
            if parsed_obj is None:
                parsed_obj = getattr(resp, "parsed", None)
            if parsed_obj is None:
                output = getattr(resp, "output", None)
                if isinstance(output, list) and output:
                    first = output[0]
                    # Nested parsed on item or first content element
                    parsed_obj = getattr(first, "parsed", None)
                    if parsed_obj is None and isinstance(first, dict):
                        parsed_obj = first.get("parsed")
                    if parsed_obj is None:
                        content = getattr(first, "content", None) or (
                            first.get("content")
                            if isinstance(first, dict)
                            else None
                        )
                        if isinstance(content, list) and content:
                            c0 = content[0]
                            if isinstance(c0, dict):
                                parsed_obj = c0.get("parsed")

        msg = BaseMessage(
            role_name="assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict={},
            content=text or "",
            parsed=parsed_obj if isinstance(parsed_obj, BaseModel) else None,
        )

        # usage is provider-specific; attach raw when present
        usage_raw: Optional[Dict[str, Any]] = None
        usage_obj = getattr(resp, "usage", None)
        try:
            if usage_obj is not None:
                usage_raw = (
                    usage_obj.model_dump()  # type: ignore[attr-defined]
                    if hasattr(usage_obj, "model_dump")
                    else dict(usage_obj)
                    if isinstance(usage_obj, dict)
                    else None
                )
        except Exception:
            usage_raw = None

        return CamelModelResponse(
            id=getattr(resp, "id", ""),
            model=getattr(resp, "model", None),
            created=getattr(resp, "created", None),
            output_messages=[msg],
            finish_reasons=["stop"],
            usage={
                "raw": usage_raw,
            },  # type: ignore[arg-type]
            raw=resp,
        )

    # ----------------------- BaseModelBackend API -----------------------
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion, ChatCompletion
    ]:  # unused legacy types in signature
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
        request_dict.update(body)

        # Tools: Responses also accepts `tools`; pass through when provided
        if tools:
            request_dict["tools"] = tools

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
            return self._to_camel_response_from_responses(
                resp, expected_parsed_type=response_format
            )  # type: ignore[return-value]
        else:
            resp = self._client.responses.create(
                model=self.model_type, **request_dict
            )
            return self._to_camel_response_from_responses(resp)  # type: ignore[return-value]

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, ChatCompletion]:
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
        request_dict.update(body)
        if tools:
            request_dict["tools"] = tools

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
            return self._to_camel_response_from_responses(
                resp, expected_parsed_type=response_format
            )  # type: ignore[return-value]
        else:
            resp = await self._async_client.responses.create(
                model=self.model_type, **request_dict
            )
            return self._to_camel_response_from_responses(resp)  # type: ignore[return-value]
