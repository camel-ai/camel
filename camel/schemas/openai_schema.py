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


# examples/agents/openai-server/openai_schema.py
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel


class ChatCompletionMessage(BaseModel):
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    refusal: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    audio: Optional[Dict[str, Any]] = None
    frequency_penalty: Optional[float] = None
    function_call: Optional[Dict[str, Any]] = None
    functions: Optional[List[Dict[str, Any]]] = None
    logit_bias: Optional[Dict[str, int]] = None
    logprobs: Optional[bool] = None
    max_completion_tokens: Optional[int] = None
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    modalities: Optional[List[Literal["text", "audio"]]] = None
    n: Optional[int] = None
    parallel_tool_calls: Optional[bool] = None
    prediction: Optional[Dict[str, Any]] = None
    presence_penalty: Optional[float] = None
    prompt_cache_key: Optional[str] = None
    reasoning_effort: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    safety_identifier: Optional[str] = None
    seed: Optional[int] = None
    service_tier: Optional[
        Literal["auto", "default", "flex", "scale", "priority"]
    ] = None
    stop: Optional[Union[str, List[str]]] = None
    store: Optional[bool] = None
    stream: Optional[bool] = False
    stream_options: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 1.0
    tool_choice: Optional[Any] = None
    tools: Optional[List[Dict[str, Any]]] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = 1.0
    user: Optional[str] = None
    verbosity: Optional[Literal["low", "medium", "high"]] = None
    web_search_options: Optional[Dict[str, Any]] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionMessage
    finish_reason: Literal[
        "stop", "length", "tool_calls", "content_filter", "function_call"
    ]


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    service_tier: Optional[
        Literal["auto", "default", "flex", "scale", "priority"]
    ] = None
    system_fingerprint: Optional[str] = None
    usage: Optional[ChatCompletionUsage] = None
