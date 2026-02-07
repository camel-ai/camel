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

import base64
import json
import os
import re
import time
import warnings
from typing import (
    Any,
    Dict,
    Generator,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import BaseModel

from camel.configs import BedrockConfig
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)

if os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true":
    try:
        from langfuse.decorators import observe
    except ImportError:
        from camel.utils import observe
else:
    from camel.utils import observe


class AWSBedrockConverseModel(BaseModelBackend):
    r"""AWS Bedrock Converse API backend with prompt caching support."""

    @api_keys_required(
        [
            ("api_key", "AWS_BEARER_TOKEN_BEDROCK"),
            ("region_name", "AWS_REGION"),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        region_name: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = BedrockConfig().as_dict()
        api_key = (
            api_key
            or os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
            or os.environ.get("BEDROCK_API_KEY")
        )
        region_name = region_name or os.environ.get("AWS_REGION")

        self._cache_control = model_config_dict.pop("cache_control", None)
        self._cache_checkpoint_target = model_config_dict.pop(
            "cache_checkpoint_target",
            "both",
        )

        if self._cache_control is not None and self._cache_control not in (
            "5m",
            "1h",
        ):
            raise ValueError(
                f"Invalid cache_control value: {self._cache_control!r}. "
                "Must be either '5m' or '1h'."
            )
        if self._cache_checkpoint_target not in (
            "system",
            "last_user",
            "both",
        ):
            raise ValueError(
                "Invalid cache_checkpoint_target value: "
                f"{self._cache_checkpoint_target!r}. Must be one of "
                "'system', 'last_user', or 'both'."
            )

        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=None,
            token_counter=token_counter,
            timeout=timeout or float(os.environ.get("MODEL_TIMEOUT", 180)),
            max_retries=max_retries,
        )

        bedrock_client = kwargs.pop("bedrock_client", None)
        self._bedrock_client = bedrock_client
        self._region_name = region_name

    @property
    def bedrock_client(self) -> Any:
        if self._bedrock_client is None:
            client_kwargs: Dict[str, Any] = {}
            if self._region_name is not None:
                client_kwargs["region_name"] = self._region_name
            if self._api_key is not None:
                os.environ["AWS_BEARER_TOKEN_BEDROCK"] = self._api_key

            import boto3  # type: ignore[import-untyped]

            self._bedrock_client = boto3.client(
                "bedrock-runtime",
                **client_kwargs,
            )
        return self._bedrock_client

    @property
    def token_counter(self) -> BaseTokenCounter:
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    @property
    def stream(self) -> bool:
        return self.model_config_dict.get("stream", False)

    @staticmethod
    def _new_cache_point(ttl: str) -> Dict[str, Any]:
        return {"cachePoint": {"type": "default", "ttl": ttl}}

    @staticmethod
    def _parse_json_or_text(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return {"json": value}
        if isinstance(value, list):
            return {"json": value}
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return {"text": ""}
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, (dict, list)):
                    return {"json": parsed}
                return {"text": stripped}
            except Exception:
                return {"text": value}
        return {"text": str(value)}

    @staticmethod
    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: List[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    txt = item.get("text")
                    if isinstance(txt, str):
                        chunks.append(txt)
            return "".join(chunks)
        return str(content)

    @staticmethod
    def _parse_data_image(url: str) -> Optional[Dict[str, Any]]:
        # Bedrock image blocks support bytes; convert data URLs only.
        m = re.match(r"^data:image/([a-zA-Z0-9+.-]+);base64,(.+)$", url)
        if not m:
            return None
        image_format = m.group(1).lower().replace("jpg", "jpeg")
        payload = m.group(2)
        try:
            image_bytes = base64.b64decode(payload, validate=True)
        except Exception:
            return None
        return {
            "image": {
                "format": image_format,
                "source": {"bytes": image_bytes},
            }
        }

    def _to_bedrock_content_blocks(
        self,
        content: Any,
    ) -> List[Dict[str, Any]]:
        if isinstance(content, str):
            return [{"text": content}]

        blocks: List[Dict[str, Any]] = []
        if not isinstance(content, list):
            return blocks

        for item in content:
            if isinstance(item, str):
                blocks.append({"text": item})
                continue
            if not isinstance(item, dict):
                continue

            if item.get("type") == "text" and isinstance(
                item.get("text"), str
            ):
                blocks.append({"text": item["text"]})
                continue

            if isinstance(item.get("text"), str):
                blocks.append({"text": item["text"]})
                continue

            if item.get("type") == "image_url":
                image_url = item.get("image_url", {})
                if isinstance(image_url, dict):
                    url = image_url.get("url")
                    if isinstance(url, str):
                        image_block = self._parse_data_image(url)
                        if image_block:
                            blocks.append(image_block)
                        else:
                            warnings.warn(
                                "Only data URL images are supported for "
                                "Bedrock Converse image content. Skipping "
                                "non-data URL image.",
                                UserWarning,
                                stacklevel=3,
                            )
                continue

            if "image" in item and isinstance(item["image"], dict):
                blocks.append({"image": item["image"]})

        return blocks

    def _convert_openai_to_bedrock_messages(
        self,
        messages: List[OpenAIMessage],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        system_parts: List[str] = []
        bedrock_messages: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                system_parts.append(self._extract_text(msg.get("content")))
                continue

            if role in ("user", "assistant"):
                content_blocks = self._to_bedrock_content_blocks(
                    msg.get("content")
                )

                if role == "assistant":
                    tool_calls = msg.get("tool_calls")
                    if isinstance(tool_calls, list):
                        for call in tool_calls:
                            if not isinstance(call, dict):
                                continue
                            function = call.get("function", {})
                            if not isinstance(function, dict):
                                continue
                            name = function.get("name")
                            if not isinstance(name, str) or not name:
                                continue
                            call_id = (
                                call.get("id") or f"tool_{int(time.time())}"
                            )
                            raw_args = function.get("arguments", "{}")
                            try:
                                parsed_args = (
                                    json.loads(raw_args)
                                    if isinstance(raw_args, str)
                                    else raw_args
                                )
                            except Exception:
                                parsed_args = {}
                            content_blocks.append(
                                {
                                    "toolUse": {
                                        "toolUseId": str(call_id),
                                        "name": name,
                                        "input": parsed_args
                                        if isinstance(parsed_args, dict)
                                        else {},
                                    }
                                }
                            )

                if content_blocks:
                    bedrock_messages.append(
                        {"role": role, "content": content_blocks}
                    )
                continue

            if role == "tool":
                tool_id = msg.get("tool_call_id")
                if not isinstance(tool_id, str) or not tool_id:
                    continue
                payload = self._parse_json_or_text(msg.get("content", ""))
                bedrock_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "toolResult": {
                                    "toolUseId": tool_id,
                                    "content": [payload],
                                }
                            }
                        ],
                    }
                )

        system_blocks: List[Dict[str, Any]] = []
        if system_parts:
            system_blocks = [
                {"text": "\n".join(part for part in system_parts if part)}
            ]

        if self._cache_control:
            if (
                self._cache_checkpoint_target in ("system", "both")
                and system_blocks
            ):
                system_blocks.append(
                    self._new_cache_point(self._cache_control)
                )

            if self._cache_checkpoint_target in ("last_user", "both"):
                for bedrock_msg in reversed(bedrock_messages):
                    if bedrock_msg.get("role") == "user":
                        msg_content = bedrock_msg.get("content")
                        if isinstance(msg_content, list):
                            msg_content.append(
                                self._new_cache_point(self._cache_control)
                            )
                        break

        return system_blocks, bedrock_messages

    def _convert_openai_tools_to_bedrock(
        self,
        tools: Optional[List[Dict[str, Any]]],
    ) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None

        bedrock_tools: List[Dict[str, Any]] = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            function = tool.get("function")
            if not isinstance(function, dict):
                continue
            name = function.get("name")
            if not isinstance(name, str) or not name:
                continue
            description = function.get("description", "")
            params = function.get("parameters", {"type": "object"})
            if not isinstance(params, dict):
                params = {"type": "object"}

            bedrock_tools.append(
                {
                    "toolSpec": {
                        "name": name,
                        "description": description,
                        "inputSchema": {"json": params},
                    }
                }
            )

        return bedrock_tools or None

    def _convert_tool_choice(
        self, tool_choice: Any
    ) -> Optional[Dict[str, Any]]:
        if tool_choice is None:
            return None
        if tool_choice == "auto":
            return {"auto": {}}
        if tool_choice == "required":
            return {"any": {}}
        if tool_choice == "none":
            return None
        if isinstance(tool_choice, dict):
            if tool_choice.get("type") == "function":
                function = tool_choice.get("function", {})
                if isinstance(function, dict) and isinstance(
                    function.get("name"), str
                ):
                    return {"tool": {"name": function["name"]}}
            if "tool" in tool_choice:
                return {"tool": tool_choice["tool"]}
        return None

    def _build_converse_request(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        request: Dict[str, Any] = {"modelId": str(self.model_type)}
        system_blocks, bedrock_messages = (
            self._convert_openai_to_bedrock_messages(messages)
        )
        request["messages"] = bedrock_messages
        if system_blocks:
            request["system"] = system_blocks

        inference_config: Dict[str, Any] = {}
        max_tokens = self.model_config_dict.get("max_tokens")
        temperature = self.model_config_dict.get("temperature")
        top_p = self.model_config_dict.get("top_p")
        stop = self.model_config_dict.get("stop")
        if isinstance(max_tokens, int):
            inference_config["maxTokens"] = max_tokens
        if isinstance(temperature, (int, float)):
            inference_config["temperature"] = float(temperature)
        if isinstance(top_p, (int, float)):
            inference_config["topP"] = float(top_p)
        if isinstance(stop, list):
            inference_config["stopSequences"] = stop
        if inference_config:
            request["inferenceConfig"] = inference_config

        additional_fields: Dict[str, Any] = {}
        if self.model_config_dict.get("top_k") is not None:
            additional_fields["top_k"] = self.model_config_dict["top_k"]
        if self.model_config_dict.get("reasoning_effort") is not None:
            additional_fields["reasoning_effort"] = self.model_config_dict[
                "reasoning_effort"
            ]
        if additional_fields:
            request["additionalModelRequestFields"] = additional_fields

        resolved_tools = tools
        if resolved_tools is None:
            config_tools = self.model_config_dict.get("tools")
            resolved_tools = (
                config_tools if isinstance(config_tools, list) else None
            )

        if self.model_config_dict.get("tool_choice") == "none":
            resolved_tools = None

        bedrock_tools = self._convert_openai_tools_to_bedrock(resolved_tools)
        if bedrock_tools:
            tool_config: Dict[str, Any] = {"tools": bedrock_tools}
            converted_choice = self._convert_tool_choice(
                self.model_config_dict.get("tool_choice")
            )
            if converted_choice:
                tool_config["toolChoice"] = converted_choice
            request["toolConfig"] = tool_config

        return request

    @staticmethod
    def _map_stop_reason(stop_reason: Optional[str]) -> str:
        return {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            "tool_use": "tool_calls",
        }.get(stop_reason or "", "stop")

    def _convert_converse_to_openai_response(
        self,
        response: Dict[str, Any],
        model: str,
    ) -> ChatCompletion:
        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        text_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            if isinstance(block.get("text"), str):
                text_parts.append(block["text"])
                continue
            tool_use = block.get("toolUse")
            if not isinstance(tool_use, dict):
                continue
            tool_id = str(tool_use.get("toolUseId", ""))
            tool_name = str(tool_use.get("name", ""))
            tool_input = tool_use.get("input", {})
            tool_calls.append(
                {
                    "id": tool_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(
                            tool_input, ensure_ascii=False
                        ),
                    },
                }
            )

        usage_raw = response.get("usage", {}) or {}
        prompt_tokens = int(usage_raw.get("inputTokens", 0) or 0)
        completion_tokens = int(usage_raw.get("outputTokens", 0) or 0)
        cache_read_tokens = int(usage_raw.get("cacheReadInputTokens", 0) or 0)
        cache_write_tokens = int(
            usage_raw.get("cacheWriteInputTokens", 0) or 0
        )

        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_tokens_details": {
                "cached_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens,
            },
        }

        message_payload: Dict[str, Any] = {
            "role": "assistant",
            "content": "".join(text_parts),
        }
        if tool_calls:
            message_payload["tool_calls"] = tool_calls

        request_id = (
            response.get("ResponseMetadata", {}).get("RequestId")
            or f"chatcmpl-bedrock-{int(time.time())}"
        )
        finish_reason = self._map_stop_reason(response.get("stopReason"))

        return ChatCompletion.construct(
            id=request_id,
            choices=[
                {
                    "index": 0,
                    "message": message_payload,
                    "finish_reason": finish_reason,
                }
            ],
            created=int(time.time()),
            model=model,
            object="chat.completion",
            usage=usage,
        )

    def _converse_stream_to_openai_chunks(
        self,
        stream_obj: Dict[str, Any],
        model: str,
    ) -> Generator[ChatCompletionChunk, None, None]:
        request_id = f"chatcmpl-bedrock-stream-{int(time.time())}"
        block_to_tool_idx: Dict[int, int] = {}
        next_tool_idx = 0
        finish_reason_sent = False

        for event in stream_obj.get("stream", []):
            if "messageStart" in event:
                yield ChatCompletionChunk.construct(
                    id=request_id,
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )
                continue

            if "contentBlockStart" in event:
                start = event["contentBlockStart"].get("start", {})
                block_idx = int(
                    event["contentBlockStart"].get("contentBlockIndex", 0)
                )
                tool_use = start.get("toolUse")
                if isinstance(tool_use, dict):
                    block_to_tool_idx[block_idx] = next_tool_idx
                    tool_id = str(tool_use.get("toolUseId", ""))
                    tool_name = str(tool_use.get("name", ""))
                    yield ChatCompletionChunk.construct(
                        id=request_id,
                        choices=[
                            {
                                "index": 0,
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": next_tool_idx,
                                            "id": tool_id,
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": "",
                                            },
                                        }
                                    ]
                                },
                                "finish_reason": None,
                            }
                        ],
                        created=int(time.time()),
                        model=model,
                        object="chat.completion.chunk",
                    )
                    next_tool_idx += 1
                continue

            if "contentBlockDelta" in event:
                delta_obj = event["contentBlockDelta"].get("delta", {})
                block_idx = int(
                    event["contentBlockDelta"].get("contentBlockIndex", 0)
                )

                if isinstance(delta_obj.get("text"), str):
                    yield ChatCompletionChunk.construct(
                        id=request_id,
                        choices=[
                            {
                                "index": 0,
                                "delta": {"content": delta_obj["text"]},
                                "finish_reason": None,
                            }
                        ],
                        created=int(time.time()),
                        model=model,
                        object="chat.completion.chunk",
                    )
                    continue

                tool_use = delta_obj.get("toolUse")
                if isinstance(tool_use, dict):
                    raw_input = tool_use.get("input", "")
                    if isinstance(raw_input, str):
                        argument_delta = raw_input
                    else:
                        argument_delta = json.dumps(
                            raw_input, ensure_ascii=False
                        )
                    mapped_idx = block_to_tool_idx.get(block_idx, 0)
                    yield ChatCompletionChunk.construct(
                        id=request_id,
                        choices=[
                            {
                                "index": 0,
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": mapped_idx,
                                            "function": {
                                                "arguments": argument_delta
                                            },
                                        }
                                    ]
                                },
                                "finish_reason": None,
                            }
                        ],
                        created=int(time.time()),
                        model=model,
                        object="chat.completion.chunk",
                    )
                continue

            if "metadata" in event:
                usage_obj = event["metadata"].get("usage", {}) or {}
                prompt_tokens = int(usage_obj.get("inputTokens", 0) or 0)
                completion_tokens = int(usage_obj.get("outputTokens", 0) or 0)
                cache_read_tokens = int(
                    usage_obj.get("cacheReadInputTokens", 0) or 0
                )
                cache_write_tokens = int(
                    usage_obj.get("cacheWriteInputTokens", 0) or 0
                )

                yield ChatCompletionChunk.construct(
                    id=request_id,
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                    usage={
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                        "prompt_tokens_details": {
                            "cached_tokens": cache_read_tokens,
                            "cache_write_tokens": cache_write_tokens,
                        },
                    },
                )
                continue

            if "messageStop" in event:
                reason = event["messageStop"].get("stopReason")
                finish_reason = self._map_stop_reason(reason)
                finish_reason_sent = True
                yield ChatCompletionChunk.construct(
                    id=request_id,
                    choices=[
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": finish_reason,
                        }
                    ],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )

        if not finish_reason_sent:
            yield ChatCompletionChunk.construct(
                id=request_id,
                choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                created=int(time.time()),
                model=model,
                object="chat.completion.chunk",
            )

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        Generator[ChatCompletionChunk, None, None],
    ]:
        if response_format is not None:
            warnings.warn(
                "The 'response_format' parameter is not supported by "
                "Bedrock Converse and will be ignored.",
                UserWarning,
                stacklevel=2,
            )

        request = self._build_converse_request(messages, tools=tools)
        if self.model_config_dict.get("stream", False):
            stream_resp = self.bedrock_client.converse_stream(**request)
            return self._converse_stream_to_openai_chunks(
                stream_obj=stream_resp, model=str(self.model_type)
            )

        response = self.bedrock_client.converse(**request)
        return self._convert_converse_to_openai_response(
            response=response, model=str(self.model_type)
        )

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> NoReturn:
        raise NotImplementedError(
            "Async inference is not supported for AWSBedrockConverseModel "
            "because boto3 Bedrock Runtime client is synchronous. "
            "Use `_run` instead."
        )
