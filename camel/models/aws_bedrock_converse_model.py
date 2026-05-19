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

import asyncio
import base64
import json
import os
import re
import time
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import uuid4

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
    r"""AWS Bedrock Converse API backend with prompt caching support.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Dict[str, Any], optional): A dictionary that will
            be fed into the backend constructor. If :obj:`None`,
            :obj:`BedrockConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (str, optional): The API key for authenticating with the
            AWS Bedrock service. (default: :obj:`None`)
        region_name (str, optional): The AWS region name, e.g.
            ``"us-east-1"``. (default: :obj:`None`)
        aws_access_key_id (str, optional): Explicit IAM access key ID.
            (default: :obj:`None`)
        aws_secret_access_key (str, optional): Explicit IAM secret access
            key. (default: :obj:`None`)
        aws_session_token (str, optional): Temporary session token for STS
            credentials. (default: :obj:`None`)
        url (str, optional): Custom endpoint URL for the Bedrock
            Runtime service (e.g. VPC endpoint). Falls back to
            the ``BEDROCK_API_BASE_URL`` environment variable.
            (default: :obj:`None`)
        token_counter (BaseTokenCounter, optional): Token counter to use
            for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (float, optional): The timeout value in seconds for API
            calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API
            calls. (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.

    References:
        https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
    """

    @api_keys_required(
        [
            ("region_name", "AWS_REGION"),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        url: Optional[str] = None,
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
            or None
        )
        region_name = region_name or os.environ.get("AWS_REGION")

        self._cache_ttl = model_config_dict.pop("cache_control", None)

        if self._cache_ttl is not None and self._cache_ttl not in (
            "5m",
            "1h",
        ):
            raise ValueError(
                f"Invalid cache_control value: {self._cache_ttl!r}. "
                "Must be either '5m' or '1h'."
            )

        url = url or os.environ.get("BEDROCK_API_BASE_URL") or None

        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout or float(os.environ.get("MODEL_TIMEOUT", 180)),
            max_retries=max_retries,
        )

        bedrock_client = kwargs.pop("bedrock_client", None)
        self._bedrock_client = bedrock_client
        self._region_name = region_name
        self._aws_access_key_id = aws_access_key_id or os.environ.get(
            "AWS_ACCESS_KEY_ID"
        )
        self._aws_secret_access_key = aws_secret_access_key or os.environ.get(
            "AWS_SECRET_ACCESS_KEY"
        )
        self._aws_session_token = aws_session_token or os.environ.get(
            "AWS_SESSION_TOKEN"
        )

    @property
    def bedrock_client(self) -> Any:
        if self._bedrock_client is None:
            client_kwargs: Dict[str, Any] = {}
            if self._region_name is not None:
                client_kwargs["region_name"] = self._region_name

            if self._api_key:
                # Bearer Token authentication via env var.
                # boto3 does not support passing bearer tokens as a
                # session/client parameter yet; env var is the only way.
                # See: https://github.com/boto/boto3/issues/4723
                os.environ["AWS_BEARER_TOKEN_BEDROCK"] = self._api_key
            elif self._aws_access_key_id and self._aws_secret_access_key:
                # Explicit IAM credentials
                client_kwargs["aws_access_key_id"] = self._aws_access_key_id
                client_kwargs["aws_secret_access_key"] = (
                    self._aws_secret_access_key
                )
                if self._aws_session_token:
                    client_kwargs["aws_session_token"] = (
                        self._aws_session_token
                    )
            # Otherwise: boto3 default credential chain
            # (env vars, ~/.aws/credentials, instance profile, etc.)

            if self._url:
                client_kwargs["endpoint_url"] = self._url

            import boto3

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
    def _new_cache_point(ttl: Optional[str] = None) -> Dict[str, Any]:
        # The Bedrock default cache TTL is 5 minutes.  When a non-default
        # TTL is requested (e.g. "1h") we must include it explicitly in
        # the cache point; otherwise the "ttl" key is omitted and the
        # service uses its 5-minute default.
        cp: Dict[str, Any] = {"type": "default"}
        if ttl and ttl != "5m":
            cp["ttl"] = ttl
        return {"cachePoint": cp}

    @staticmethod
    def _parse_json_or_text(value: Any) -> Dict[str, Any]:
        # Bedrock Converse requires `toolResult.content[].json` objects.
        if isinstance(value, dict):
            return {"json": value}
        if isinstance(value, list):
            return {"json": {"__camel_tool_result__": value}}
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return {"text": ""}
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return {"json": parsed}
                if isinstance(parsed, list):
                    return {"json": {"__camel_tool_result__": parsed}}
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
        # Bedrock Converse supports jpeg, png, gif, and webp image formats.
        # Only base64-encoded data URLs are converted here.
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
            return [{"text": content}] if content else []

        blocks: List[Dict[str, Any]] = []
        if not isinstance(content, list):
            return blocks

        for item in content:
            if isinstance(item, str):
                blocks.append({"text": item})
                continue
            if not isinstance(item, dict):
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
                                call.get("id") or f"tool_{uuid4().hex[:8]}"
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
                tool_result_block = {
                    "toolResult": {
                        "toolUseId": tool_id,
                        "content": [payload],
                    }
                }
                # Bedrock Converse requires all toolResult blocks for a
                # multi-tool-use assistant turn to be grouped in a single
                # user message immediately following that assistant turn.
                # When the previous bedrock message is already a user
                # message (i.e. from a prior tool result in the same
                # batch), append to it instead of creating a new one.
                if (
                    bedrock_messages
                    and bedrock_messages[-1].get("role") == "user"
                    and isinstance(bedrock_messages[-1].get("content"), list)
                    and any(
                        isinstance(b, dict) and "toolResult" in b
                        for b in bedrock_messages[-1]["content"]
                    )
                ):
                    bedrock_messages[-1]["content"].append(tool_result_block)
                else:
                    bedrock_messages.append(
                        {
                            "role": "user",
                            "content": [tool_result_block],
                        }
                    )

        system_blocks: List[Dict[str, Any]] = []
        if system_parts:
            system_blocks = [
                {"text": "\n".join(part for part in system_parts if part)}
            ]

        if self._cache_ttl:
            if system_blocks:
                system_blocks.append(self._new_cache_point(self._cache_ttl))

            for bedrock_msg in reversed(bedrock_messages):
                if bedrock_msg.get("role") == "user":
                    msg_content = bedrock_msg.get("content")
                    if isinstance(msg_content, list):
                        msg_content.append(
                            self._new_cache_point(self._cache_ttl)
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

    @staticmethod
    def _ensure_additional_properties_false(
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recursively set ``additionalProperties: false`` on all object
        types in *schema*.  AWS Bedrock requires this or it raises a
        ``ValidationException``."""
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        for key in ("properties", "$defs", "definitions"):
            container = schema.get(key)
            if isinstance(container, dict):
                for v in container.values():
                    if isinstance(v, dict):
                        AWSBedrockConverseModel._ensure_additional_properties_false(
                            v
                        )
        for key in ("allOf", "anyOf", "oneOf"):
            variants = schema.get(key)
            if isinstance(variants, list):
                for v in variants:
                    if isinstance(v, dict):
                        AWSBedrockConverseModel._ensure_additional_properties_false(
                            v
                        )
        items = schema.get("items")
        if isinstance(items, dict):
            AWSBedrockConverseModel._ensure_additional_properties_false(items)
        return schema

    @staticmethod
    def _convert_response_format_to_output_config(
        response_format: Type[BaseModel],
    ) -> Dict[str, Any]:
        schema = response_format.model_json_schema()
        AWSBedrockConverseModel._ensure_additional_properties_false(schema)
        return {
            "textFormat": {
                "type": "json_schema",
                "structure": {
                    "jsonSchema": {
                        "schema": json.dumps(schema, ensure_ascii=False),
                        "name": response_format.__name__,
                        "description": schema.get(
                            "description",
                            "Structured output for "
                            f"{response_format.__name__}",
                        ),
                    }
                },
            }
        }

    def _build_converse_request(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Type[BaseModel]] = None,
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

        if response_format is not None:
            request["outputConfig"] = (
                self._convert_response_format_to_output_config(response_format)
            )

        return request

    @staticmethod
    def _map_stop_reason(stop_reason: Optional[str]) -> str:
        return {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            "tool_use": "tool_calls",
        }.get(stop_reason or "", "stop")

    @staticmethod
    def _parse_bedrock_usage(usage_raw: Dict[str, Any]) -> Dict[str, Any]:
        prompt_tokens = int(usage_raw.get("inputTokens", 0) or 0)
        completion_tokens = int(usage_raw.get("outputTokens", 0) or 0)
        cache_read = int(usage_raw.get("cacheReadInputTokens", 0) or 0)
        cache_write = int(usage_raw.get("cacheWriteInputTokens", 0) or 0)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_tokens_details": {
                "cached_tokens": cache_read,
                "cache_write_tokens": cache_write,
            },
        }

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

        usage = self._parse_bedrock_usage(response.get("usage", {}) or {})

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

        def _make_chunk(**kwargs: Any) -> ChatCompletionChunk:
            return ChatCompletionChunk.construct(
                id=request_id,
                created=int(time.time()),
                model=model,
                object="chat.completion.chunk",
                **kwargs,
            )

        for event in stream_obj.get("stream", []):
            if "messageStart" in event:
                yield _make_chunk(
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}]
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
                    yield _make_chunk(
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
                        ]
                    )
                    next_tool_idx += 1
                continue

            if "contentBlockDelta" in event:
                delta_obj = event["contentBlockDelta"].get("delta", {})
                block_idx = int(
                    event["contentBlockDelta"].get("contentBlockIndex", 0)
                )

                if isinstance(delta_obj.get("text"), str):
                    yield _make_chunk(
                        choices=[
                            {
                                "index": 0,
                                "delta": {"content": delta_obj["text"]},
                                "finish_reason": None,
                            }
                        ]
                    )
                    continue

                tool_use = delta_obj.get("toolUse")
                if isinstance(tool_use, dict):
                    raw_input = tool_use.get("input", "")
                    argument_delta = (
                        raw_input
                        if isinstance(raw_input, str)
                        else json.dumps(raw_input, ensure_ascii=False)
                    )
                    mapped_idx = block_to_tool_idx.get(block_idx, 0)
                    yield _make_chunk(
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
                        ]
                    )
                continue

            if "metadata" in event:
                usage = self._parse_bedrock_usage(
                    event["metadata"].get("usage", {}) or {}
                )
                yield _make_chunk(
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    usage=usage,
                )
                continue

            if "messageStop" in event:
                reason = event["messageStop"].get("stopReason")
                finish_reason_sent = True
                yield _make_chunk(
                    choices=[
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": self._map_stop_reason(reason),
                        }
                    ]
                )

        if not finish_reason_sent:
            yield _make_chunk(
                choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}]
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
        request = self._build_converse_request(
            messages,
            tools=tools,
            response_format=response_format,
        )
        if self.model_config_dict.get("stream", False):
            stream_resp = self.bedrock_client.converse_stream(**request)
            return self._converse_stream_to_openai_chunks(
                stream_obj=stream_resp, model=str(self.model_type)
            )
        response = self.bedrock_client.converse(**request)
        return self._convert_converse_to_openai_response(
            response=response, model=str(self.model_type)
        )

    async def _arun_stream(
        self,
        request: Dict[str, Any],
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        stream_resp = await asyncio.to_thread(
            self.bedrock_client.converse_stream, **request
        )
        # boto3 streams are synchronous iterators; collect in a thread
        # then yield asynchronously.  True incremental bridging would
        # require a thread-safe queue, which adds complexity for little
        # gain given that the underlying I/O is already synchronous.
        chunks = await asyncio.to_thread(
            lambda: list(
                self._converse_stream_to_openai_chunks(
                    stream_obj=stream_resp,
                    model=str(self.model_type),
                )
            )
        )
        for chunk in chunks:
            yield chunk

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        AsyncGenerator[ChatCompletionChunk, None],
    ]:
        request = self._build_converse_request(
            messages,
            tools=tools,
            response_format=response_format,
        )
        if self.model_config_dict.get("stream", False):
            return self._arun_stream(request)
        response = await asyncio.to_thread(
            self.bedrock_client.converse, **request
        )
        return self._convert_converse_to_openai_response(
            response=response, model=str(self.model_type)
        )
