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
"""Model-agnostic message abstractions and converters.

Introduces `CamelMessage` to decouple CAMEL from the legacy
OpenAI Chat Completions message schema while keeping behaviour identical
via adapter conversion.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, cast

from pydantic import BaseModel, Field

from camel.messages import OpenAIMessage


class CamelContentPart(BaseModel):
    """A single content fragment.

    Extend to cover Responses API inputs while staying compatible
    with Chat Completions. Supported types:
      - text, image_url (Chat-compatible)
      - input_text, input_image, input_file, input_audio (Responses-compatible)
    """

    type: Literal[
        "text",
        "image_url",
        "input_text",
        "input_image",
        "input_file",
        "input_audio",
        "function_call_output",
    ]
    payload: Dict[str, Any] = Field(default_factory=dict)


class CamelMessage(BaseModel):
    """A model-agnostic chat message used by CAMEL runtime.

    The schema is compatible with both legacy Chat Completions and the
    newer Responses API after conversion.
    """

    role: Literal["system", "user", "assistant", "tool", "developer"]
    content: List[CamelContentPart] = Field(default_factory=list)
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def openai_messages_to_camel(
    messages: List[OpenAIMessage],
) -> List[CamelMessage]:
    """Convert OpenAI ChatCompletion-style messages to `CamelMessage`."""
    result: List[CamelMessage] = []
    for msg in messages:
        role = msg.get("role", "user")  # type: ignore[assignment]
        parts: List[CamelContentPart] = []

        content = msg.get("content")
        if isinstance(content, str):
            if content.strip():
                parts.append(
                    CamelContentPart(type="text", payload={"text": content})
                )
        elif isinstance(content, list):
            for item in content:
                item_t = item.get("type") if isinstance(item, dict) else None
                if item_t == "text":
                    text = item.get("text", "")
                    parts.append(
                        CamelContentPart(type="text", payload={"text": text})
                    )
                elif item_t == "input_text":
                    text = item.get("text", "")
                    parts.append(
                        CamelContentPart(
                            type="input_text", payload={"text": text}
                        )
                    )
                elif item_t == "image_url":
                    image_url = item.get("image_url", {})
                    payload = {
                        "url": image_url.get("url"),
                        "detail": image_url.get("detail"),
                    }
                    parts.append(
                        CamelContentPart(type="image_url", payload=payload)
                    )
                elif item_t == "input_image":
                    image_url = item.get("image_url", "")
                    if isinstance(image_url, dict):
                        image_url = image_url.get("url", "")
                    payload = {"url": image_url}
                    parts.append(
                        CamelContentPart(type="input_image", payload=payload)
                    )
                elif item_t == "input_audio":
                    input_audio = item.get("input_audio", {})
                    payload = {
                        "data": input_audio.get("data"),
                        "format": input_audio.get("format"),
                    }
                    parts.append(
                        CamelContentPart(type="input_audio", payload=payload)
                    )
                elif item_t == "input_file":
                    # input_file can have file_id, file_url, or file_data
                    payload = {}
                    if "file_id" in item:
                        payload["file_id"] = item["file_id"]
                    if "file_url" in item:
                        payload["file_url"] = item["file_url"]
                    if "file_data" in item:
                        payload["file_data"] = item["file_data"]

                    parts.append(
                        CamelContentPart(type="input_file", payload=payload)
                    )

        name_val = cast(Optional[str], msg.get("name", None))
        tool_call_id = (
            cast(Optional[str], msg.get("tool_call_id", None))
            if role == "tool"
            else None
        )

        result.append(
            CamelMessage(
                role=cast(Any, role),  # mypy: role literal narrowing from dict
                content=parts,
                name=name_val,
                tool_call_id=tool_call_id,
            )
        )

    return result


def camel_messages_to_openai(
    messages: List[CamelMessage],
) -> List[OpenAIMessage]:
    """Convert `CamelMessage` back to OpenAI ChatCompletion-style messages."""
    result: List[OpenAIMessage] = []
    for cmsg in messages:
        if cmsg.role == "tool":
            # Tool message expects string content + tool_call_id
            text_parts = [
                p.payload.get("text", "")
                for p in cmsg.content
                if p.type == "text"
            ]
            content_str = "\n".join([t for t in text_parts if t])
            d: Dict[str, Any] = {"role": "tool", "content": content_str}
            if cmsg.tool_call_id:
                d["tool_call_id"] = cmsg.tool_call_id
            result.append(cast(OpenAIMessage, d))
            continue

        # Non-tool roles: use hybrid content list
        hybrid: List[Dict[str, Any]] = []
        for part in cmsg.content:
            if part.type == "text":
                hybrid.append(
                    {"type": "text", "text": part.payload.get("text", "")}
                )
            elif part.type == "input_text":
                # Responses-style input_text -> Chat text for compatibility
                hybrid.append(
                    {
                        "type": "text",
                        "text": part.payload.get("text", ""),
                    }
                )
            elif part.type == "image_url":
                url = part.payload.get("url")
                detail = part.payload.get("detail") or "auto"
                hybrid.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": url, "detail": detail},
                    }
                )
            elif part.type == "input_image":
                # Responses-style input_image -> Chat image_url schema
                url = part.payload.get("url") or part.payload.get("image_url")
                detail = part.payload.get("detail") or "auto"
                hybrid.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": url, "detail": detail},
                    }
                )
            elif part.type == "input_audio":
                payload = part.payload
                hybrid.append(
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": payload.get("data"),
                            "format": payload.get("format"),
                        },
                    }
                )
            elif part.type == "input_file":
                payload = part.payload
                item = {"type": "input_file"}
                if "file_id" in payload:
                    item["file_id"] = payload["file_id"]
                if "file_url" in payload:
                    item["file_url"] = payload["file_url"]
                if "file_data" in payload:
                    item["file_data"] = payload["file_data"]
                hybrid.append(item)

        d = {"role": cmsg.role, "content": hybrid or ""}
        if cmsg.name and cmsg.role in {
            "system",
            "user",
            "assistant",
            "developer",
        }:
            d["name"] = cmsg.name
        result.append(cast(OpenAIMessage, d))

    return result


def _part_to_responses_fragment(part: CamelContentPart) -> Dict[str, Any]:
    """Convert a single CamelContentPart into a Responses API content item.

    Mapping rules:
      - text         -> {type: input_text, text}
      - image_url    -> {type: input_image, image_url}
      - input_text   -> passthrough as {type: input_text, text}
      - input_image  -> passthrough as {type: input_image, image_url}
      - input_file   -> {type: input_file, file_id|file_url}
      - input_audio  -> {type: input_audio, input_audio: {data, format}}
      - function_call_output -> {type: function_call_output, call_id, output}
    """
    t = part.type
    p = part.payload or {}

    if t == "text" or t == "input_text":
        text_val = p.get("text", "")
        return {"type": "input_text", "text": text_val}

    if t == "image_url" or t == "input_image":
        url = p.get("image_url") or p.get("url")
        return {"type": "input_image", "image_url": url}

    if t == "input_file":
        if "file_id" in p:
            return {"type": "input_file", "file_id": p.get("file_id")}
        if "file_url" in p:
            return {"type": "input_file", "file_url": p.get("file_url")}
        # Fallback: allow data URL
        if "file_data" in p:
            return {"type": "input_file", "file_data": p.get("file_data")}
        return {"type": "input_file"}

    if t == "input_audio":
        audio = {
            "data": p.get("data"),
            "format": p.get("format", "wav"),
        }
        return {"type": "input_audio", "input_audio": audio}

    if t == "function_call_output":
        return {
            "type": "function_call_output",
            "call_id": p.get("call_id"),
            "output": p.get("output"),
        }

    # Default safe fallback: treat as text
    return {"type": "input_text", "text": str(p.get("text", ""))}


def camel_messages_to_responses_request(
    messages: List[CamelMessage],
) -> Dict[str, Any]:
    """Build a minimal Responses API request body shape.

    Returns a dict with optional `instructions` and an `input` list of
    message objects, where each message has a `role` and typed `content`.

    Notes:
      - System messages are concatenated into `instructions` (in order).
      - Non-system messages are emitted as `role: user` items for maximal
        compatibility (Responses tolerates user/assistant; we default to user).
      - Chat-only parts (text/image_url) converted to input_text/input_image.
    """
    instructions_parts: List[str] = []
    input_messages: List[Dict[str, Any]] = []

    for msg in messages:
        if msg.role == "system" or msg.role == "developer":
            # Fold into instructions
            for part in msg.content:
                frag = _part_to_responses_fragment(part)
                if frag.get("type") == "input_text":
                    txt = frag.get("text") or ""
                    if txt:
                        instructions_parts.append(str(txt))
            continue

        if msg.role == "tool":
            # Convert tool outputs into function_call_output content
            call_id = msg.tool_call_id
            output_texts: List[str] = []
            for part in msg.content:
                if part.type == "function_call_output":
                    output_val = part.payload.get("output")
                    if output_val is not None:
                        output_texts.append(str(output_val))
                elif part.type in {"text", "input_text"}:
                    txt = part.payload.get("text")
                    if txt:
                        output_texts.append(str(txt))

            content_frags = [
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": "\n".join(output_texts) if output_texts else "",
                }
            ]
            input_messages.append(
                {
                    "role": "assistant",  # function outputs go here
                    "content": content_frags,
                }
            )
            continue

        # Map other roles to Responses-supported roles (user/assistant)
        role = "assistant" if msg.role == "assistant" else "user"
        content_frags = [_part_to_responses_fragment(p) for p in msg.content]
        input_messages.append(
            {
                "role": role,
                "content": content_frags,
            }
        )

    body: Dict[str, Any] = {"input": input_messages}
    if instructions_parts:
        body["instructions"] = "\n\n".join(instructions_parts)
    return body
