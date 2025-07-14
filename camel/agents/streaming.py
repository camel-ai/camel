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
from typing import Generator, Optional, List, Dict, Any, AsyncGenerator

from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse


class StreamContentAccumulator:
    r"""Manages content accumulation across streaming responses to ensure
    all responses contain complete cumulative content."""

    def __init__(self):
        self.base_content = ""  # Content before tool calls
        self.current_content = ""  # Current streaming content
        self.tool_status_messages = []  # Accumulated tool status messages

    def set_base_content(self, content: str):
        r"""Set the base content (usually empty or pre-tool content)."""
        self.base_content = content

    def add_streaming_content(self, new_content: str):
        r"""Add new streaming content."""
        self.current_content += new_content

    def add_tool_status(self, status_message: str):
        r"""Add a tool status message."""
        self.tool_status_messages.append(status_message)

    def get_full_content(self) -> str:
        r"""Get the complete accumulated content."""
        tool_messages = "".join(self.tool_status_messages)
        return self.base_content + tool_messages + self.current_content

    def get_content_with_new_status(self, status_message: str) -> str:
        r"""Get content with a new status message appended."""
        tool_messages = "".join([*self.tool_status_messages, status_message])
        return self.base_content + tool_messages + self.current_content

    def reset_streaming_content(self):
        r"""Reset only the streaming content, keep base and tool status."""
        self.current_content = ""


class StreamingChatAgentResponse:
    r"""A wrapper that makes streaming responses compatible with
    non-streaming code.

    This class wraps a Generator[ChatAgentResponse, None, None] and provides
    the same interface as ChatAgentResponse, so existing code doesn't need to
    change.
    """

    def __init__(self, generator: Generator[ChatAgentResponse, None, None]):
        self._generator = generator
        self._current_response: Optional[ChatAgentResponse] = None
        self._responses: List[ChatAgentResponse] = []
        self._consumed = False

    def _ensure_latest_response(self):
        r"""Ensure we have the latest response by consuming the generator."""
        if not self._consumed:
            try:
                for response in self._generator:
                    self._responses.append(response)
                    self._current_response = response
                self._consumed = True
            except StopIteration:
                self._consumed = True

    @property
    def msgs(self) -> List[BaseMessage]:
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
            return iter(self._responses)
        else:
            # If not consumed, consume and yield
            try:
                for response in self._generator:
                    self._responses.append(response)
                    self._current_response = response
                    yield response
                self._consumed = True
            except StopIteration:
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
        self, async_generator: AsyncGenerator[ChatAgentResponse, None]
    ):
        self._async_generator = async_generator
        self._current_response: Optional[ChatAgentResponse] = None
        self._responses: List[ChatAgentResponse] = []
        self._consumed = False

    async def _ensure_latest_response(self):
        r"""Ensure the latest response by consuming the async generator."""
        if not self._consumed:
            try:
                async for response in self._async_generator:
                    self._responses.append(response)
                    self._current_response = response
                self._consumed = True
            except StopAsyncIteration:
                self._consumed = True

    async def _get_final_response(self) -> ChatAgentResponse:
        r"""Get the final response after consuming the entire stream."""
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
                try:
                    async for response in self._async_generator:
                        self._responses.append(response)
                        self._current_response = response
                        yield response
                    self._consumed = True
                except StopAsyncIteration:
                    self._consumed = True

            return _consume_and_yield()