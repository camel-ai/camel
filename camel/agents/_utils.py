# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
from __future__ import annotations

import functools
import json
import logging
import re
import textwrap
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Union,
)

from camel.agents._types import ToolCallRequest
from camel.toolkits import FunctionTool
from camel.types import Choice
from camel.types.agents import ToolCallingRecord

if TYPE_CHECKING:
    from camel.messages import BaseMessage
    from camel.responses import ChatAgentResponse

logger = logging.getLogger(__name__)

# Token limit error markers for detecting context window overflow
TOKEN_LIMIT_ERROR_MARKERS = (
    "context_length_exceeded",
    "prompt is too long",
    "exceeded your current quota",
    "tokens must be reduced",
    "context length",
    "token count",
    "context limit",
)


@functools.lru_cache(maxsize=1)
def get_langfuse_session_setter() -> Optional[Callable[[str], None]]:
    """Get the langfuse session setter function, cached after first call."""
    try:
        from camel.utils.langfuse import set_current_agent_session_id

        return set_current_agent_session_id
    except ImportError:
        return None


@dataclass
class ToolOutputHistoryEntry:
    """Entry for tracking tool output history for caching purposes."""

    tool_name: str
    tool_call_id: str
    result_text: str
    record_uuids: List[str]
    record_timestamps: List[float]
    cached: bool = False


class StreamContentAccumulator:
    r"""Manages content accumulation across streaming responses to ensure
    all responses contain complete cumulative content."""

    def __init__(self):
        self.base_content = ""  # Content before tool calls
        self.current_content = []  # Accumulated streaming fragments
        self.tool_status_messages = []  # Accumulated tool status messages
        self.reasoning_content = []  # Accumulated reasoning content
        self.is_reasoning_phase = True  # Track if we're in reasoning phase

    def set_base_content(self, content: str):
        r"""Set the base content (usually empty or pre-tool content)."""
        self.base_content = content

    def add_streaming_content(self, new_content: str):
        r"""Add new streaming content."""
        self.current_content.append(new_content)
        self.is_reasoning_phase = (
            False  # Once we get content, we're past reasoning
        )

    def add_reasoning_content(self, new_reasoning: str):
        r"""Add new reasoning content."""
        self.reasoning_content.append(new_reasoning)

    def add_tool_status(self, status_message: str):
        r"""Add a tool status message."""
        self.tool_status_messages.append(status_message)

    def get_full_content(self) -> str:
        r"""Get the complete accumulated content."""
        tool_messages = "".join(self.tool_status_messages)
        current = "".join(self.current_content)
        return self.base_content + tool_messages + current

    def get_full_reasoning_content(self) -> str:
        r"""Get the complete accumulated reasoning content."""
        return "".join(self.reasoning_content)

    def get_content_with_new_status(self, status_message: str) -> str:
        r"""Get content with a new status message appended."""
        tool_messages = "".join([*self.tool_status_messages, status_message])
        current = "".join(self.current_content)
        return self.base_content + tool_messages + current

    def reset_streaming_content(self):
        r"""Reset only the streaming content, keep base and tool status."""
        self.current_content = []
        self.reasoning_content = []
        self.is_reasoning_phase = True


class StreamingChatAgentResponse:
    r"""A wrapper that makes streaming responses compatible with
    non-streaming code.

    This class wraps a Generator[ChatAgentResponse, None, None] and provides
    the same interface as ChatAgentResponse, so existing code doesn't need to
    change.
    """

    def __init__(self, generator: Generator["ChatAgentResponse", None, None]):
        self._generator = generator
        self._current_response: Optional["ChatAgentResponse"] = None
        self._responses: List["ChatAgentResponse"] = []
        self._consumed = False

    def _ensure_latest_response(self):
        r"""Ensure we have the latest response by consuming the generator."""
        if not self._consumed:
            for response in self._generator:
                self._responses.append(response)
                self._current_response = response
            self._consumed = True

    @property
    def msgs(self) -> List["BaseMessage"]:
        r"""Get messages from the latest response."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.msgs
        return []

    @property
    def terminated(self) -> bool:
        r"""Get terminated status from the latest response."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.terminated
        return False

    @property
    def info(self) -> Dict[str, Any]:
        r"""Get info from the latest response."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.info
        return {}

    @property
    def msg(self):
        r"""Get the single message if there's exactly one message."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.msg
        return None

    def __iter__(self):
        r"""Make this object iterable."""
        if self._consumed:
            # If already consumed, iterate over stored responses
            yield from self._responses
        else:
            # If not consumed, consume and yield
            for response in self._generator:
                self._responses.append(response)
                self._current_response = response
                yield response
            self._consumed = True

    def __getattr__(self, name):
        r"""Forward any other attribute access to the latest response."""
        self._ensure_latest_response()
        if self._current_response and hasattr(self._current_response, name):
            return getattr(self._current_response, name)
        raise AttributeError(
            f"'StreamingChatAgentResponse' object has no attribute '{name}'"
        )


class AsyncStreamingChatAgentResponse:
    r"""A wrapper that makes async streaming responses awaitable and
    compatible with non-streaming code.

    This class wraps an AsyncGenerator[ChatAgentResponse, None] and provides
    both awaitable and async iterable interfaces.
    """

    def __init__(
        self, async_generator: AsyncGenerator["ChatAgentResponse", None]
    ):
        self._async_generator = async_generator
        self._current_response: Optional[ChatAgentResponse] = None
        self._responses: List[ChatAgentResponse] = []
        self._consumed = False

    async def _ensure_latest_response(self):
        r"""Ensure the latest response by consuming the async generator."""
        if not self._consumed:
            async for response in self._async_generator:
                self._responses.append(response)
                self._current_response = response
            self._consumed = True

    async def _get_final_response(self) -> "ChatAgentResponse":
        r"""Get the final response after consuming the entire stream."""
        from camel.responses import ChatAgentResponse

        await self._ensure_latest_response()
        if self._current_response:
            return self._current_response
        # Return a default response if nothing was consumed
        return ChatAgentResponse(msgs=[], terminated=False, info={})

    def __await__(self):
        r"""Make this object awaitable - returns the final response."""
        return self._get_final_response().__await__()

    def __aiter__(self):
        r"""Make this object async iterable."""
        if self._consumed:
            # If already consumed, create async iterator from stored responses
            async def _async_iter():
                for response in self._responses:
                    yield response

            return _async_iter()
        else:
            # If not consumed, consume and yield
            async def _consume_and_yield():
                async for response in self._async_generator:
                    self._responses.append(response)
                    self._current_response = response
                    yield response
                self._consumed = True

            return _consume_and_yield()


def build_default_summary_prompt(conversation_text: str) -> str:
    r"""Create the default prompt used for conversation summarization.

    Args:
        conversation_text (str): The conversation to be summarized.

    Returns:
        str: A formatted prompt instructing the model to produce a structured
            markdown summary.
    """
    template = textwrap.dedent(
        """\
        Summarize the conversation below.
        Produce markdown that strictly follows this outline and numbering:

        Summary:
        1. **Primary Request and Intent**:
        2. **Key Concepts**:
        3. **Errors and Fixes**:
        4. **Problem Solving**:
        5. **Pending Tasks**:
        6. **Current Work**:
        7. **Optional Next Step**:

        Requirements:
        - Use bullet lists under each section (`- item`). If a section has no
          information, output `- None noted`.
        - Keep the ordering, headings, and formatting as written above.
        - Focus on concrete actions, findings, and decisions.
        - Do not invent details that are not supported by the conversation.

        Conversation:
        {conversation_text}
        """
    )
    return template.format(conversation_text=conversation_text)


def generate_tool_prompt(tool_schema_list: List[Dict[str, Any]]) -> str:
    r"""Generates a tool prompt based on the provided tool schema list.

    Returns:
        str: A string representing the tool prompt.
    """
    tool_prompts = []

    for tool in tool_schema_list:
        tool_info = tool["function"]
        tool_name = tool_info["name"]
        tool_description = tool_info["description"]
        tool_json = json.dumps(tool_info, indent=4, ensure_ascii=False)

        prompt = (
            f"Use the function '{tool_name}' to '{tool_description}':\n"
            f"{tool_json}\n"
        )
        tool_prompts.append(prompt)

    tool_prompt_str = "\n".join(tool_prompts)

    final_prompt = textwrap.dedent(
        f"""\
        You have access to the following functions:

        {tool_prompt_str}

        If you choose to call a function ONLY reply in the following format with no prefix or suffix:

        <function=example_function_name>{{"example_name": "example_value"}}</function>

        Reminder:
        - Function calls MUST follow the specified format, start with <function= and end with </function>
        - Required parameters MUST be specified
        - Only call one function at a time
        - Put the entire function call reply on one line
        - If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls.
        """  # noqa: E501
    )
    return final_prompt


def extract_tool_call(
    content: str,
) -> Optional[Dict[str, Any]]:
    r"""Extract the tool call from the model response, if present.

    Args:
        response (Any): The model's response object.

    Returns:
        Optional[Dict[str, Any]]: The parsed tool call if present,
            otherwise None.
    """
    function_regex = r"<function=(\w+)>(.*?)</function>"
    match = re.search(function_regex, content)

    if not match:
        return None

    function_name, args_string = match.groups()
    try:
        args = json.loads(args_string)
        return {"function": function_name, "arguments": args}
    except json.JSONDecodeError as error:
        logger.error(f"Error parsing function arguments: {error}")
        return None


def safe_model_dump(obj) -> Dict[str, Any]:
    r"""Safely dump a Pydantic model to a dictionary.

    This method attempts to use the `model_dump` method if available,
    otherwise it falls back to the `dict` method.
    """
    # Check if the `model_dump` method exists (Pydantic v2)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    # Fallback to `dict()` method (Pydantic v1)
    elif hasattr(obj, "dict"):
        return obj.dict()
    else:
        raise TypeError("The object is not a Pydantic model")


def convert_to_function_tool(
    tool: Union[FunctionTool, Callable],
) -> FunctionTool:
    r"""Convert a tool to a FunctionTool from Callable."""
    return tool if isinstance(tool, FunctionTool) else FunctionTool(tool)


def convert_to_schema(
    tool: Union[FunctionTool, Callable, Dict[str, Any]],
) -> Dict[str, Any]:
    r"""Convert a tool to a schema from Callable or FunctionTool."""
    if isinstance(tool, FunctionTool):
        return tool.get_openai_tool_schema()
    elif callable(tool):
        return FunctionTool(tool).get_openai_tool_schema()
    else:
        return tool


def get_info_dict(
    session_id: Optional[str],
    usage: Optional[Dict[str, int]],
    termination_reasons: List[str],
    num_tokens: int,
    tool_calls: List[ToolCallingRecord],
    external_tool_call_requests: Optional[List[ToolCallRequest]] = None,
) -> Dict[str, Any]:
    r"""Returns a dictionary containing information about the chat session.

    Args:
        session_id (str, optional): The ID of the chat session.
        usage (Dict[str, int], optional): Information about the usage of
            the LLM.
        termination_reasons (List[str]): The reasons for the termination
            of the chat session.
        num_tokens (int): The number of tokens used in the chat session.
        tool_calls (List[ToolCallingRecord]): The list of function
            calling records, containing the information of called tools.
        external_tool_call_requests (Optional[List[ToolCallRequest]]): The
            requests for external tool calls.


    Returns:
        Dict[str, Any]: The chat session information.
    """
    return {
        "id": session_id,
        "usage": usage,
        "termination_reasons": termination_reasons,
        "num_tokens": num_tokens,
        "tool_calls": tool_calls,
        "external_tool_call_requests": external_tool_call_requests,
    }


def handle_logprobs(choice: Choice) -> Optional[List[Dict[str, Any]]]:
    if choice.logprobs is None:
        return None

    tokens_logprobs = choice.logprobs.content

    if tokens_logprobs is None:
        return None

    return [
        {
            "token": token_logprob.token,
            "logprob": token_logprob.logprob,
            "top_logprobs": [
                (top_logprob.token, top_logprob.logprob)
                for top_logprob in token_logprob.top_logprobs
            ],
        }
        for token_logprob in tokens_logprobs
    ]
