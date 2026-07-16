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
"""SGLang client for native and OpenAI-compatible training rollouts."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Optional, Union

import httpx

from camel.messages import OpenAIMessage
from camel.types import ChatCompletion
from camel.utils import BaseTokenCounter

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL
)


@dataclass(frozen=True)
class SGLangGeneration:
    """The OpenAI-compatible response and exact token trajectory."""

    completion: ChatCompletion
    prompt_token_ids: List[int]
    output_token_ids: List[int]
    raw_response: Dict[str, Any]


class HuggingFaceTokenCounter(BaseTokenCounter):
    """CAMEL token counter backed by the client's Hugging Face tokenizer."""

    def __init__(self, tokenizer: Any, chat_template: Optional[str] = None):
        self.tokenizer = tokenizer
        self.chat_template = chat_template

    def count_tokens_from_messages(self, messages: List[OpenAIMessage]) -> int:
        encoded = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            chat_template=self.chat_template,
        )
        if isinstance(encoded, Mapping):
            encoded = encoded["input_ids"]
        if hasattr(encoded, "tolist"):
            encoded = encoded.tolist()
        if encoded and isinstance(encoded[0], list):
            encoded = encoded[0]
        return len(encoded)

    def encode(self, text: str) -> List[int]:
        return list(self.tokenizer.encode(text, add_special_tokens=False))

    def decode(self, token_ids: List[int]) -> str:
        return self.tokenizer.decode(token_ids)


class _SGLangChatCompletions:
    """OpenAI-compatible ``client.chat.completions`` namespace."""

    def __init__(self, client: "SGLangClient") -> None:
        self._client = client

    async def create(
        self,
        *,
        messages: List[OpenAIMessage],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Any = None,
        stream: bool = False,
        extra_body: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> ChatCompletion:
        """Match the non-streaming ``AsyncOpenAI`` creation interface."""
        model_config = dict(extra_body or {})
        for transport_key in ("extra_headers", "extra_query", "timeout"):
            kwargs.pop(transport_key, None)
        model_config.update(kwargs)
        model_config["stream"] = stream
        return await self._client.create_chat_completion(
            messages,
            model=model,
            tools=tools,
            model_config=model_config,
            response_format=response_format,
        )


class _SGLangChat:
    """OpenAI-compatible ``client.chat`` namespace."""

    def __init__(self, client: "SGLangClient") -> None:
        self.completions = _SGLangChatCompletions(client)


class SGLangClient:
    """Send chat messages to native or OpenAI-compatible SGLang endpoints.

    Args:
        base_url: SGLang or OpenAI-compatible server base URL.
        model: Model name recorded in the returned ChatCompletion.
        tokenizer: Hugging Face tokenizer instance or repository/path. If it
            is omitted, ``model`` is loaded with ``AutoTokenizer``.
        chat_template: A Jinja template string or a path to one. If omitted,
            the tokenizer's model-specific template is used.
        chat_template_kwargs: Extra model-specific template options such as
            ``enable_thinking=False``.
        http_client: Injectable ``httpx.AsyncClient`` for tests/custom HTTP.
        api_key: Optional bearer token for authenticated OpenAI-compatible
            endpoints.
        api_mode: ``native`` uses ``/generate`` and local tokenization;
            ``openai`` uses the standard ``/v1/chat/completions`` interface.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        tokenizer: Optional[Union[str, Any]] = None,
        chat_template: Optional[str] = None,
        chat_template_kwargs: Optional[Mapping[str, Any]] = None,
        timeout: float = 180.0,
        http_client: Optional[httpx.AsyncClient] = None,
        tokenizer_kwargs: Optional[Mapping[str, Any]] = None,
        api_mode: Literal["native", "openai"] = "native",
        api_key: Optional[str] = None,
    ) -> None:
        self.api_mode = self._validate_api_mode(api_mode)
        self.base_url = self._normalise_base_url(base_url, self.api_mode)
        self.model = model
        self.api_key = api_key
        tokenizer_source = tokenizer
        if tokenizer_source is None and self.api_mode == "native":
            tokenizer_source = model
        self.tokenizer = (
            self._load_tokenizer(
                tokenizer_source, dict(tokenizer_kwargs or {})
            )
            if tokenizer_source is not None
            else None
        )
        self.chat_template = self._load_chat_template(chat_template)
        self.chat_template_kwargs = dict(chat_template_kwargs or {})
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(timeout=timeout)
        self.token_counter = (
            HuggingFaceTokenCounter(self.tokenizer, self.chat_template)
            if self.tokenizer is not None
            else None
        )
        self.last_generation: Optional[SGLangGeneration] = None
        self.chat = _SGLangChat(self)

    @staticmethod
    def _validate_api_mode(
        api_mode: Literal["native", "openai"],
    ) -> Literal["native", "openai"]:
        if api_mode not in {"native", "openai"}:
            raise ValueError("api_mode must be one of 'native' or 'openai'")
        return api_mode

    @staticmethod
    def _normalise_base_url(
        url: str, api_mode: Literal["native", "openai"]
    ) -> str:
        url = url.rstrip("/")
        if api_mode == "native" and url.endswith("/v1"):
            return url[:-3]
        return url

    @staticmethod
    def _load_tokenizer(tokenizer: Union[str, Any], kwargs: Dict[str, Any]):
        if not isinstance(tokenizer, str):
            return tokenizer
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(tokenizer, **kwargs)

    @staticmethod
    def _load_chat_template(chat_template: Optional[str]) -> Optional[str]:
        if chat_template is None:
            return None
        candidate = Path(chat_template).expanduser()
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
        return chat_template

    def render_messages(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        """Apply the configured model template and return exact prompt IDs."""
        if self.tokenizer is None:
            raise RuntimeError(
                "A tokenizer is required to render messages in native mode"
            )
        kwargs = dict(self.chat_template_kwargs)
        if tools:
            kwargs["tools"] = tools
        token_ids = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            chat_template=self.chat_template,
            **kwargs,
        )
        if isinstance(token_ids, Mapping):
            token_ids = token_ids["input_ids"]
        if hasattr(token_ids, "tolist"):
            token_ids = token_ids.tolist()
        if token_ids and isinstance(token_ids[0], list):
            token_ids = token_ids[0]
        return [int(token_id) for token_id in token_ids]

    async def create_chat_completion(
        self,
        messages: List[OpenAIMessage],
        *,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        model_config: Optional[Mapping[str, Any]] = None,
        response_format: Any = None,
    ) -> ChatCompletion:
        """Generate and return a CAMEL/OpenAI ``ChatCompletion``."""
        request_model = model or self.model
        if self.api_mode == "openai":
            return await self._create_openai_chat_completion(
                messages,
                model=request_model,
                tools=tools,
                model_config=model_config,
                response_format=response_format,
            )

        if response_format is not None:
            raise NotImplementedError(
                "Native SGLang client does not support response_format"
            )

        prompt_token_ids = self.render_messages(messages, tools)
        sampling_params = self._sampling_params(model_config or {})
        payload = {
            "input_ids": prompt_token_ids,
            "sampling_params": sampling_params,
            "return_prompt_token_ids": True,
        }
        response = await self.http_client.post(
            f"{self.base_url}/generate",
            json=payload,
            headers=self._request_headers(),
        )
        response.raise_for_status()
        raw = response.json()
        if isinstance(raw, list):
            if len(raw) != 1:
                raise ValueError("Only one SGLang generation is supported")
            raw = raw[0]
        if not isinstance(raw, dict):
            raise TypeError("SGLang /generate returned a non-object response")

        completion = self._parse_response(
            raw, prompt_token_ids, model=request_model
        )
        generation = SGLangGeneration(
            completion=completion,
            prompt_token_ids=prompt_token_ids,
            output_token_ids=[int(x) for x in raw.get("output_ids", [])],
            raw_response=raw,
        )
        self.last_generation = generation
        return completion

    async def _create_openai_chat_completion(
        self,
        messages: List[OpenAIMessage],
        *,
        model: str,
        tools: Optional[List[Dict[str, Any]]],
        model_config: Optional[Mapping[str, Any]],
        response_format: Any,
    ) -> ChatCompletion:
        config = dict(model_config or {})
        if config.get("stream"):
            raise NotImplementedError(
                "Streaming is not supported by the rollout client"
            )

        payload = self._openai_payload(
            messages, model, tools, config, response_format
        )
        response = await self.http_client.post(
            self._chat_completions_url(),
            json=payload,
            headers=self._request_headers(),
        )
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, dict):
            raise TypeError(
                "SGLang /v1/chat/completions returned a non-object response"
            )

        prompt_token_ids = self._extract_prompt_token_ids(raw)
        output_token_ids = self._extract_output_token_ids(raw)
        body = dict(raw)
        # OpenAI's Pydantic models preserve these rollout extensions.
        body["prompt_token_ids"] = prompt_token_ids
        body["output_token_ids"] = output_token_ids
        body["raw_response"] = raw
        completion = ChatCompletion.model_validate(body)
        self.last_generation = SGLangGeneration(
            completion=completion,
            prompt_token_ids=prompt_token_ids,
            output_token_ids=output_token_ids,
            raw_response=raw,
        )
        return completion

    def _request_headers(self) -> Optional[Dict[str, str]]:
        if self.api_key is None:
            return None
        return {"Authorization": f"Bearer {self.api_key}"}

    def _chat_completions_url(self) -> str:
        if self.base_url.endswith("/v1/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def _openai_payload(
        self,
        messages: List[OpenAIMessage],
        model: str,
        tools: Optional[List[Dict[str, Any]]],
        config: Dict[str, Any],
        response_format: Any,
    ) -> Dict[str, Any]:
        config.pop("context_length", None)
        config.pop("stream", None)
        config.pop("model", None)
        config.pop("messages", None)
        config.pop("tools", None)
        max_new_tokens = config.pop("max_new_tokens", None)
        if max_new_tokens is not None and "max_tokens" not in config:
            config["max_tokens"] = max_new_tokens

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            **config,
            "stream": False,
            # SGLang returns the exact IDs used after server-side templating.
            "return_prompt_token_ids": True,
        }
        if tools is not None:
            payload["tools"] = tools
        if response_format is not None:
            if isinstance(response_format, type) and hasattr(
                response_format, "model_json_schema"
            ):
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_format.__name__,
                        "schema": response_format.model_json_schema(),
                        "strict": True,
                    },
                }
            else:
                payload["response_format"] = response_format
        return payload

    @staticmethod
    def _first_choice(raw: Mapping[str, Any]) -> Mapping[str, Any]:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            return {}
        choice = choices[0]
        return choice if isinstance(choice, Mapping) else {}

    @classmethod
    def _extract_prompt_token_ids(cls, raw: Mapping[str, Any]) -> List[int]:
        value = raw.get("prompt_token_ids")
        if value is None:
            value = cls._first_choice(raw).get("prompt_token_ids")
        if not isinstance(value, list):
            return []
        return [int(token_id) for token_id in value]

    @classmethod
    def _extract_output_token_ids(cls, raw: Mapping[str, Any]) -> List[int]:
        value = raw.get("output_token_ids")
        if isinstance(value, list):
            return [int(token_id) for token_id in value]

        meta_info = cls._first_choice(raw).get("meta_info")
        if not isinstance(meta_info, Mapping):
            return []
        logprobs = meta_info.get("output_token_logprobs")
        if not isinstance(logprobs, list):
            return []
        token_ids: List[int] = []
        for item in logprobs:
            if isinstance(item, (list, tuple)) and len(item) > 1:
                token_ids.append(int(item[1]))
            elif isinstance(item, Mapping) and "token_id" in item:
                token_ids.append(int(item["token_id"]))
        return token_ids

    @staticmethod
    def _sampling_params(config: Mapping[str, Any]) -> Dict[str, Any]:
        allowed = {
            "temperature",
            "top_p",
            "top_k",
            "min_p",
            "frequency_penalty",
            "presence_penalty",
            "repetition_penalty",
            "stop",
            "stop_token_ids",
            "ignore_eos",
            "skip_special_tokens",
            "spaces_between_special_tokens",
            "n",
            "seed",
        }
        result = {
            key: value for key, value in config.items() if key in allowed
        }
        max_tokens = config.get("max_tokens", config.get("max_new_tokens"))
        if max_tokens is not None:
            result["max_new_tokens"] = max_tokens
        return result

    def _parse_response(
        self,
        raw: Dict[str, Any],
        prompt_token_ids: List[int],
        *,
        model: str,
    ) -> ChatCompletion:
        text = raw.get("text") or ""
        output_ids = [int(x) for x in raw.get("output_ids", [])]
        tool_calls = self._parse_tool_calls(text)
        content = _TOOL_CALL_RE.sub("", text).strip() if tool_calls else text
        meta = raw.get("meta_info") or {}
        finish = meta.get("finish_reason", "stop")
        if isinstance(finish, dict):
            finish = finish.get("type", "stop")
        if tool_calls:
            finish = "tool_calls"

        prompt_count = int(meta.get("prompt_tokens") or len(prompt_token_ids))
        completion_count = int(
            meta.get("completion_tokens") or len(output_ids)
        )
        body: Dict[str, Any] = {
            "id": str(
                meta.get("id") or raw.get("id") or f"sglang-{uuid.uuid4()}"
            ),
            "model": model,
            "object": "chat.completion",
            "created": int(time.time()),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content or None,
                        "tool_calls": tool_calls or None,
                    },
                    "finish_reason": finish,
                    "logprobs": None,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_count,
                "completion_tokens": completion_count,
                "total_tokens": prompt_count + completion_count,
            },
            # Pydantic's OpenAI models preserve these training extensions.
            "prompt_token_ids": prompt_token_ids,
            "output_token_ids": output_ids,
            "raw_response": raw,
        }
        return ChatCompletion.model_validate(body)

    @staticmethod
    def _parse_tool_calls(text: str) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        for index, match in enumerate(_TOOL_CALL_RE.finditer(text)):
            try:
                value = json.loads(match.group(1))
                name = value["name"]
                arguments = value.get("arguments", {})
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                calls.append(
                    {
                        "id": f"call_{uuid.uuid4().hex}",
                        "index": index,
                        "type": "function",
                        "function": {"name": name, "arguments": arguments},
                    }
                )
            except (KeyError, TypeError, json.JSONDecodeError):
                continue
        return calls

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self.http_client.aclose()

    async def close(self) -> None:
        """Match ``AsyncOpenAI.close`` for interchangeable client cleanup."""
        await self.aclose()


__all__ = [
    "HuggingFaceTokenCounter",
    "SGLangClient",
    "SGLangGeneration",
]
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
