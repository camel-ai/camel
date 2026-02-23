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
from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

from google import genai
from google.genai import types
from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import GeminiConfig
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
    dependencies_required,
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


def _safe_json_loads(value: Any) -> Optional[Any]:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None


def _guess_mime_type(uri: str) -> Optional[str]:
    mime_type, _ = mimetypes.guess_type(uri)
    return mime_type


class GeminiModel(BaseModelBackend):
    r"""Gemini API via Google Gen AI SDK in a unified BaseModelBackend.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of Gemini series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into Gemini generate_content config. If
            :obj:`None`, :obj:`GeminiConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Gemini service. (default: :obj:`None`)
        url (Optional[str], optional): Custom base URL for Gemini API.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter` will
            be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        client (Optional[Any], optional): A custom synchronous GenAI client.
            (default: :obj:`None`)
        async_client (Optional[Any], optional): A custom asynchronous GenAI
            client. (default: :obj:`None`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @dependencies_required("google.genai")
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = GeminiConfig().as_dict()

        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        base_url = url or os.environ.get("GEMINI_API_BASE_URL")

        if timeout is None:
            timeout = float(os.environ.get("MODEL_TIMEOUT", 180))

        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=base_url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
        )

        if client is not None:
            self._client = client
            self._async_client = async_client or getattr(client, "aio", None)
            return

        client_kwargs: Dict[str, Any] = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["http_options"] = types.HttpOptions(
                base_url=base_url,
            )

        client_kwargs.update(kwargs)
        self._client = genai.Client(**client_kwargs)
        self._async_client = async_client or getattr(self._client, "aio", None)

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            OpenAITokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def _normalize_function_parameters(
        self, parameters: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(parameters, dict):
            return parameters

        normalized = json.loads(json.dumps(parameters))

        def _scrub(obj: Any) -> None:
            if isinstance(obj, dict):
                obj.pop("additional_properties", None)
                obj.pop("additionalProperties", None)
                for value in obj.values():
                    _scrub(value)
            elif isinstance(obj, list):
                for item in obj:
                    _scrub(item)

        def _fix_properties(schema: Dict[str, Any]) -> None:
            r"""Recursively fix anyOf/enum/format in all nested properties."""
            props = schema.get("properties")
            if not isinstance(props, dict):
                return

            for prop_name, prop_value in list(props.items()):
                if not isinstance(prop_value, dict):
                    continue

                # Flatten anyOf → take first variant, preserve description.
                if "anyOf" in prop_value:
                    first_type = prop_value["anyOf"][0]
                    desc = prop_value.get("description")
                    props[prop_name] = first_type
                    if desc is not None:
                        props[prop_name]["description"] = desc
                    prop_value = props[prop_name]

                if not isinstance(prop_value, dict):
                    continue

                # Strip enum/format that Gemini doesn't accept on
                # non-string / non-numeric types.
                if prop_value.get("type") != "string":
                    prop_value.pop("enum", None)
                if prop_value.get("type") not in (
                    "string",
                    "integer",
                    "number",
                ):
                    prop_value.pop("format", None)

                # Recurse into nested object schemas.
                _fix_properties(prop_value)

                # Also handle array item schemas.
                items = prop_value.get("items")
                if isinstance(items, dict):
                    _fix_properties(items)

        _fix_properties(normalized)
        _scrub(normalized)
        return normalized

    def _resolve_tool_choice(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Any]]:
        r"""Resolve tool_choice into a (tools, ToolConfig) pair.

        Returns:
            Tuple of (tools list or None, ToolConfig or None).
        """
        tool_choice = self.model_config_dict.get("tool_choice")
        if not tools or not tool_choice:
            return tools, None

        if tool_choice == "none":
            return None, types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.NONE
                )
            )

        if tool_choice == "required":
            return tools, types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.ANY
                )
            )

        if isinstance(tool_choice, dict):
            func = tool_choice.get("function", {})
            func_name = func.get("name") if isinstance(func, dict) else None
            if func_name:
                return tools, types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.ANY,
                        allowed_function_names=[func_name],
                    )
                )

        return tools, None

    def _convert_openai_tools_to_genai(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Any]]:
        if not tools:
            return None

        declarations = []
        for tool in tools:
            if tool.get("type") != "function":
                continue
            func = tool.get("function", {})
            name = func.get("name")
            if not name:
                continue
            params = func.get("parameters")
            params = self._normalize_function_parameters(params)
            declarations.append(
                types.FunctionDeclaration(
                    name=name,
                    description=func.get("description"),
                    parameters_json_schema=params,
                )
            )

        if not declarations:
            return None

        return [types.Tool(function_declarations=declarations)]

    def _content_to_parts(self, content: Any) -> List[Any]:
        parts: List[Any] = []
        if content is None:
            return parts

        if isinstance(content, str):
            parts.append(types.Part(text=content))
            return parts

        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    parts.append(types.Part(text=item))
                    continue
                if not isinstance(item, dict):
                    continue
                part_type = item.get("type")
                if part_type == "text":
                    text = item.get("text", "")
                    parts.append(types.Part(text=text))
                elif part_type == "image_url":
                    image_url = item.get("image_url", {})
                    if isinstance(image_url, dict):
                        uri = image_url.get("url")
                    else:
                        uri = image_url
                    if uri:
                        if isinstance(uri, str) and uri.startswith("data:"):
                            try:
                                header, b64_data = uri.split(",", 1)
                                mime_type = header.split(";")[0].split(":")[1]
                                image_bytes = base64.b64decode(b64_data)
                                parts.append(
                                    types.Part.from_bytes(
                                        data=image_bytes,
                                        mime_type=mime_type,
                                    )
                                )
                            except Exception:
                                pass
                        else:
                            mime = _guess_mime_type(uri)
                            if mime:
                                parts.append(
                                    types.Part.from_uri(
                                        file_uri=uri, mime_type=mime
                                    )
                                )
                            else:
                                parts.append(types.Part.from_uri(file_uri=uri))
            return parts

        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(types.Part(text=text))
        return parts

    def _make_function_call_part(
        self,
        name: str,
        args: Optional[Any],
        thought_signature: Optional[Any] = None,
    ) -> Any:
        args = args if args is not None else {}
        if hasattr(types.Part, "from_function_call"):
            part = types.Part.from_function_call(name=name, args=args)
            if thought_signature is not None and hasattr(
                part, "thought_signature"
            ):
                part.thought_signature = thought_signature
            return part

        return types.Part(
            function_call=types.FunctionCall(name=name, args=args),
            thought_signature=thought_signature,
        )

    def _make_function_response_part(self, name: str, response: Any) -> Any:
        if hasattr(types.Part, "from_function_response"):
            return types.Part.from_function_response(
                name=name, response=response
            )

        return types.Part(
            function_response=types.FunctionResponse(
                name=name,
                response=response,
            )
        )

    @staticmethod
    def _extract_thought_signature(
        tool_call: Dict[str, Any],
    ) -> Optional[str]:
        r"""Extract thought_signature from a tool call's extra_content."""
        extra = tool_call.get("extra_content")
        if not isinstance(extra, dict):
            extra = tool_call.get("function", {}).get("extra_content")
        if not isinstance(extra, dict):
            return None
        google_extra = extra.get("google", {})
        if isinstance(google_extra, dict):
            sig = google_extra.get("thought_signature")
            if sig:
                return sig
        return extra.get("thought_signature") or None

    @staticmethod
    def _has_thought_signature(tool_calls: List[Dict[str, Any]]) -> bool:
        r"""Return True if any tool call carries a thought_signature."""
        return any(
            GeminiModel._extract_thought_signature(tc) is not None
            for tc in tool_calls
        )

    def _process_messages(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""Re-group split parallel tool calls back into a single assistant
        message."""
        if not messages:
            return messages

        result: List[OpenAIMessage] = []
        i = 0

        while i < len(messages):
            msg = messages[i]

            if msg.get("role") != "assistant" or not msg.get("tool_calls"):  # type: ignore[typeddict-item]
                result.append(msg)
                i += 1
                continue

            # Check whether this leading assistant has a thought_signature.
            tool_calls_val = cast(List[Dict[str, Any]], msg["tool_calls"])  # type: ignore[typeddict-item]
            has_sig = self._has_thought_signature(tool_calls_val)
            if not has_sig:
                # No signature → not a thinking-model parallel split, or
                # it is a continuation Part (no sig).  Emit as-is.
                result.append(msg)
                i += 1
                continue

            # This assistant has a signature.  Look ahead to see if the
            # next assistant→tool pairs are signature-less continuations
            # (= parallel companions that should be merged).
            merged_tool_calls: List[Dict[str, Any]] = list(tool_calls_val)
            # Track which tool_call_ids belong to this merged batch.
            merged_call_ids: set = {
                tc.get("id") for tc in merged_tool_calls if tc.get("id")
            }
            tool_messages: List[OpenAIMessage] = []
            content_parts: List[str] = []
            msg_content = msg.get("content")
            if isinstance(msg_content, str) and msg_content:
                content_parts.append(msg_content)

            j = i + 1

            # Consume the tool results that follow the first assistant,
            # only if their tool_call_id belongs to the current batch.
            while j < len(messages) and messages[j].get("role") == "tool":
                if (
                    merged_call_ids
                    and messages[j].get("tool_call_id") not in merged_call_ids
                ):
                    break
                tool_messages.append(messages[j])
                j += 1

            # Now look for additional assistant(no-sig)→tool+ pairs.
            while j < len(messages):
                next_msg = messages[j]
                if next_msg.get("role") != "assistant" or not next_msg.get(
                    "tool_calls"
                ):
                    break

                # If this assistant has its own signature → new sequential
                # step; stop merging.
                next_tool_calls = cast(
                    List[Dict[str, Any]],
                    next_msg["tool_calls"],  # type: ignore[typeddict-item]
                )
                if self._has_thought_signature(next_tool_calls):
                    break

                # It's a parallel companion
                for tc in next_tool_calls:
                    merged_tool_calls.append(tc)
                    tc_id = tc.get("id")
                    if tc_id:
                        merged_call_ids.add(tc_id)
                next_content = next_msg.get("content")
                if isinstance(next_content, str) and next_content:
                    content_parts.append(next_content)
                j += 1

                # Consume tool results for this companion, checking id.
                while j < len(messages) and messages[j].get("role") == "tool":
                    if (
                        merged_call_ids
                        and messages[j].get("tool_call_id")
                        not in merged_call_ids
                    ):
                        break
                    tool_messages.append(messages[j])
                    j += 1

            if len(merged_tool_calls) == len(tool_calls_val):
                # Nothing extra was merged
                result.append(msg)
                result.extend(tool_messages)
                i = j
                continue

            merged_content = "\n".join(content_parts) if content_parts else ""
            merged_assistant = cast(
                OpenAIMessage,
                {
                    "role": "assistant",
                    "content": merged_content,
                    "tool_calls": merged_tool_calls,
                },
            )
            result.append(merged_assistant)
            result.extend(tool_messages)
            i = j

        return result

    def _convert_openai_messages_to_genai(
        self,
        messages: List[OpenAIMessage],
    ) -> Tuple[Optional[str], List[Any]]:
        system_texts: List[str] = []
        contents: List[Any] = []
        tool_call_name_map: Dict[str, str] = {}

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                if isinstance(content, str) and content.strip():
                    system_texts.append(content)
                elif isinstance(content, list):
                    text_parts = [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict)
                        and item.get("type") == "text"
                    ]
                    if text_parts:
                        system_texts.append("".join(text_parts))
                continue

            if role == "assistant":
                parts = self._content_to_parts(content)
                tool_calls_raw: Any = msg.get("tool_calls") or []  # type: ignore[typeddict-item]
                for tool_call in tool_calls_raw:
                    func = tool_call.get("function", {})
                    name = func.get("name", "")
                    if not name:
                        continue
                    call_id = tool_call.get("id")
                    if call_id:
                        tool_call_name_map[call_id] = name
                    args = func.get("arguments")
                    args_obj = _safe_json_loads(args)
                    if args_obj is None:
                        args_obj = {}
                    thought_signature = self._extract_thought_signature(
                        tool_call
                    )

                    parts.append(
                        self._make_function_call_part(
                            name, args_obj, thought_signature
                        )
                    )

                if not parts:
                    parts = [types.Part(text="")]

                contents.append(types.Content(role="model", parts=parts))
                continue

            if role == "tool":
                tool_call_id = cast(str, msg.get("tool_call_id", ""))
                tool_name = tool_call_name_map.get(tool_call_id, "")
                response_payload = _safe_json_loads(content)
                if response_payload is None:
                    response_payload = {"result": content}
                elif not isinstance(response_payload, dict):
                    response_payload = {"result": response_payload}
                parts = [
                    self._make_function_response_part(
                        tool_name, response_payload
                    )
                ]
                contents.append(types.Content(role="user", parts=parts))
                continue

            parts = self._content_to_parts(content)
            if not parts:
                parts = [types.Part(text="")]
            contents.append(types.Content(role="user", parts=parts))

        # Gemini API rejects consecutive Contents with the same role.
        # This happens when multiple tool messages map to consecutive
        # user Contents.  Merge them by combining their parts.
        merged_contents: List[Any] = []
        for c in contents:
            if merged_contents and getattr(
                merged_contents[-1], "role", None
            ) == getattr(c, "role", None):
                merged_contents[-1].parts.extend(c.parts)
            else:
                merged_contents.append(c)

        system_instruction = "\n".join(system_texts).strip() or None
        return system_instruction, merged_contents

    def _response_format_config(
        self, response_format: Optional[Union[Type[BaseModel], Dict[str, Any]]]
    ) -> Dict[str, Any]:
        if response_format is None:
            return {}

        if isinstance(response_format, type) and issubclass(
            response_format, BaseModel
        ):
            return {
                "response_mime_type": "application/json",
                "response_schema": response_format,
            }

        if isinstance(response_format, dict):
            # OpenAI-style {"type":"json_object"} -> request JSON output
            if response_format.get("type") == "json_object":
                return {"response_mime_type": "application/json"}

            schema_like = any(
                key in response_format
                for key in ("properties", "$schema", "$defs", "type")
            )
            if schema_like:
                return {
                    "response_mime_type": "application/json",
                    "response_json_schema": response_format,
                }

        raise ValueError(
            "Unsupported response_format for Gemini. Use a Pydantic model, "
            "OpenAI-style {'type': 'json_object'}, or a JSON schema dict."
        )

    def _build_generate_config(
        self,
        tools: Optional[List[Any]],
        system_instruction: Optional[str],
        response_format: Optional[Union[Type[BaseModel], Dict[str, Any]]],
        tool_config: Optional[Any] = None,
    ) -> Any:
        config_kwargs: Dict[str, Any] = {}

        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        temperature = self.model_config_dict.get("temperature")
        if temperature is not None:
            config_kwargs["temperature"] = temperature

        top_p = self.model_config_dict.get("top_p")
        if top_p is not None:
            config_kwargs["top_p"] = top_p

        max_tokens = self.model_config_dict.get("max_tokens")
        if max_tokens is not None:
            config_kwargs["max_output_tokens"] = max_tokens

        stop = self.model_config_dict.get("stop")
        if stop is not None:
            if isinstance(stop, (list, tuple)):
                config_kwargs["stop_sequences"] = list(stop)
            else:
                config_kwargs["stop_sequences"] = [stop]

        candidate_count = self.model_config_dict.get("n")
        if candidate_count is not None:
            config_kwargs["candidate_count"] = candidate_count

        if tools:
            config_kwargs["tools"] = tools

        if tool_config is not None:
            config_kwargs["tool_config"] = tool_config

        config_kwargs.update(self._response_format_config(response_format))

        return types.GenerateContentConfig(**config_kwargs)

    def _extract_usage(self, response: Any) -> Optional[Dict[str, int]]:
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return None

        prompt = getattr(usage, "prompt_token_count", None)
        completion = getattr(usage, "candidates_token_count", None)
        total = getattr(usage, "total_token_count", None)

        if prompt is None and completion is None and total is None:
            return None

        if total is None:
            total = (prompt or 0) + (completion or 0)

        return {
            "prompt_tokens": int(prompt or 0),
            "completion_tokens": int(completion or 0),
            "total_tokens": int(total or 0),
        }

    @staticmethod
    def _map_finish_reason(raw_finish: Any) -> Optional[str]:
        r"""Map a Gemini finish reason to an OpenAI-compatible string."""
        if raw_finish is None:
            return None
        raw = getattr(raw_finish, "value", str(raw_finish)).lower()
        _MAPPING = {
            "stop": "stop",
            "end_turn": "stop",
            "stop_sequence": "stop",
            "max_tokens": "length",
            "length": "length",
            "tool_calls": "tool_calls",
            "tool_use": "tool_calls",
            "function_call": "tool_calls",
            "safety": "content_filter",
            "content_filter": "content_filter",
        }
        return _MAPPING.get(raw, raw)

    @staticmethod
    def _parse_function_call_part(
        part: Any, fallback_id: str
    ) -> Optional[Dict[str, Any]]:
        r"""Extract function call info from a GenAI Part (object or dict).

        Returns an OpenAI-style tool_call dict, or None if the part is not
        a function call.
        """
        # SDK object path
        if hasattr(part, "function_call") and not isinstance(part, dict):
            func_call = part.function_call
            if func_call is None:
                return None
            name = getattr(func_call, "name", "")
            args = getattr(func_call, "args", {})
            args_text = (
                args if isinstance(args, str) else json.dumps(args or {})
            )
            thought_signature = getattr(part, "thought_signature", None)
            tc: Dict[str, Any] = {
                "id": getattr(func_call, "id", None) or fallback_id,
                "type": "function",
                "function": {"name": name, "arguments": args_text},
            }
            if thought_signature is not None:
                tc["extra_content"] = {
                    "google": {"thought_signature": thought_signature}
                }
            return tc

        # Plain dict path
        if isinstance(part, dict) and "function_call" in part:
            func_call = part["function_call"]
            name = func_call.get("name", "")
            args = func_call.get("args", {})
            args_text = (
                args if isinstance(args, str) else json.dumps(args or {})
            )
            thought_signature = part.get("thought_signature")
            tc = {
                "id": func_call.get("id") or fallback_id,
                "type": "function",
                "function": {"name": name, "arguments": args_text},
            }
            if thought_signature is not None:
                tc["extra_content"] = {
                    "google": {"thought_signature": thought_signature}
                }
            return tc

        return None

    def _convert_genai_response_to_openai(
        self, response: Any, model: str
    ) -> ChatCompletion:
        candidates = getattr(response, "candidates", []) or []
        choices = []

        for index, candidate in enumerate(candidates):
            text_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []

            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", []) if content else []

            for part in parts or []:
                # Text
                text = (
                    getattr(part, "text", None)
                    if not isinstance(part, dict)
                    else part.get("text")
                )
                if text:
                    text_parts.append(text)
                    continue

                # Function call
                tc = self._parse_function_call_part(
                    part, f"call_{index}_{len(tool_calls)}"
                )
                if tc is not None:
                    tool_calls.append(tc)

            finish_reason = self._map_finish_reason(
                getattr(candidate, "finish_reason", None)
            )
            if tool_calls and finish_reason is None:
                finish_reason = "tool_calls"

            message: Dict[str, Any] = {
                "role": "assistant",
                "content": "".join(text_parts),
            }
            if tool_calls:
                message["tool_calls"] = tool_calls

            choices.append(
                {
                    "index": index,
                    "message": message,
                    "finish_reason": finish_reason,
                }
            )

        if not choices:
            choices.append(
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop",
                }
            )

        usage = self._extract_usage(response)

        return ChatCompletion.construct(
            id=getattr(response, "id", f"chatcmpl-{int(time.time())}"),
            choices=choices,
            created=int(time.time()),
            model=model,
            object="chat.completion",
            usage=usage,
        )

    def _convert_genai_stream_to_openai_chunk(
        self,
        chunk: Any,
        model: str,
        tool_call_index: Dict[str, int],
    ) -> ChatCompletionChunk:
        delta_content = ""
        tool_calls: Optional[List[Dict[str, Any]]] = None
        finish_reason = None
        chunk_id = getattr(chunk, "id", "")

        candidates = getattr(chunk, "candidates", []) or []
        if candidates:
            candidate = candidates[0]
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", []) if content else []

            tool_calls_list: List[Dict[str, Any]] = []
            for part in parts or []:
                if hasattr(part, "text") and part.text:
                    delta_content += part.text
                    continue
                if hasattr(part, "function_call"):
                    func_call = part.function_call
                    tool_id = str(
                        getattr(func_call, "id", None)
                        or getattr(func_call, "name", "")
                    )
                    if tool_id not in tool_call_index:
                        tool_call_index[tool_id] = len(tool_call_index)
                    idx = tool_call_index[tool_id]
                    tc = self._parse_function_call_part(part, f"call_{idx}")
                    if tc is not None:
                        tc["index"] = idx
                        tool_calls_list.append(tc)

            if tool_calls_list:
                tool_calls = tool_calls_list

            finish_reason = self._map_finish_reason(
                getattr(candidate, "finish_reason", None)
            )

        delta: Dict[str, Any] = {}
        if delta_content:
            delta["content"] = delta_content
        if tool_calls:
            delta["tool_calls"] = tool_calls

        usage = self._extract_usage(chunk)

        return ChatCompletionChunk.construct(
            id=chunk_id or f"chatcmpl-{int(time.time())}",
            choices=[
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }
            ],
            created=int(time.time()),
            model=model,
            object="chat.completion.chunk",
            usage=usage,
        )

    def _wrap_genai_stream(
        self, stream: Any, model: str
    ) -> Stream[ChatCompletionChunk]:
        tool_call_index: Dict[str, int] = {}

        def _generate():
            for chunk in stream:
                yield self._convert_genai_stream_to_openai_chunk(
                    chunk, model, tool_call_index
                )

        return cast(Stream[ChatCompletionChunk], _generate())

    def _wrap_genai_async_stream(
        self, stream: Any, model: str
    ) -> AsyncStream[ChatCompletionChunk]:
        tool_call_index: Dict[str, int] = {}

        async def _generate():
            async for chunk in stream:
                yield self._convert_genai_stream_to_openai_chunk(
                    chunk, model, tool_call_index
                )

        return cast(AsyncStream[ChatCompletionChunk], _generate())

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of Gemini chat completion."""
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        messages = self._process_messages(messages)
        tools, tool_config = self._resolve_tool_choice(tools)
        system_instruction, contents = self._convert_openai_messages_to_genai(
            messages
        )
        genai_tools = self._convert_openai_tools_to_genai(tools)
        config = self._build_generate_config(
            genai_tools, system_instruction, response_format, tool_config
        )

        is_streaming = self.model_config_dict.get("stream", False)
        if is_streaming:
            stream = self._client.models.generate_content_stream(
                model=str(self.model_type),
                contents=contents,
                config=config,
            )
            return self._wrap_genai_stream(stream, str(self.model_type))

        response = self._client.models.generate_content(
            model=str(self.model_type),
            contents=contents,
            config=config,
        )
        return self._convert_genai_response_to_openai(
            response, str(self.model_type)
        )

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of Gemini chat completion in async mode."""
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        messages = self._process_messages(messages)

        if self._async_client is None:
            raise RuntimeError("Async client is not available for Gemini API.")

        tools, tool_config = self._resolve_tool_choice(tools)
        system_instruction, contents = self._convert_openai_messages_to_genai(
            messages
        )
        genai_tools = self._convert_openai_tools_to_genai(tools)
        config = self._build_generate_config(
            genai_tools, system_instruction, response_format, tool_config
        )

        is_streaming = self.model_config_dict.get("stream", False)
        if is_streaming:
            stream = await self._async_client.models.generate_content_stream(
                model=str(self.model_type),
                contents=contents,
                config=config,
            )
            return self._wrap_genai_async_stream(stream, str(self.model_type))

        response = await self._async_client.models.generate_content(
            model=str(self.model_type),
            contents=contents,
            config=config,
        )
        return self._convert_genai_response_to_openai(
            response, str(self.model_type)
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode."""
        return self.model_config_dict.get("stream", False)
