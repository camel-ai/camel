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

from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.types import ChatCompletion, ChatCompletionChunk

logger = get_logger(__name__)


class InterleavedThinkingMixin:
    r"""Mixin class for models that support interleaved thinking.

    This mixin provides shared functionality for handling reasoning content
    in multi-turn conversations with tool calls. Models like ZhipuAI,
    Moonshot, Minimax, and Volcano require the reasoning content from a
    model response to be passed back in subsequent requests for proper
    context management.

    Class attributes:
        _reasoning_field (str): The field name used for reasoning content.
            Defaults to "reasoning_content". Subclasses can override this
            (e.g., Minimax uses "reasoning_details").

    Instance attributes:
        _last_reasoning (Optional[Any]): Stores the reasoning content from
            the last model response to be injected into the next request.
    """

    # Field name for reasoning content - subclasses can override
    _reasoning_field: str = "reasoning_content"

    # Type hints for attributes that should exist on the model class
    model_config_dict: Dict[str, Any]

    def _init_thinking_state(self) -> None:
        r"""Initialize the thinking state.

        Should be called in the subclass's __init__ method after
        super().__init__().
        """
        self._last_reasoning: Optional[Any] = None

    def _is_thinking_enabled(self) -> bool:
        r"""Check if interleaved thinking mode is enabled.

        Returns:
            bool: True if interleaved_thinking is enabled in the model config.
        """
        return bool(self.model_config_dict.get("interleaved_thinking", False))

    def _extract_reasoning(self, response: ChatCompletion) -> Optional[Any]:
        r"""Extract reasoning content from the model response.

        Args:
            response: The model response.

        Returns:
            The reasoning content if available, None otherwise.
        """
        if response.choices:
            return getattr(
                response.choices[0].message, self._reasoning_field, None
            )
        return None

    def _inject_reasoning(
        self,
        messages: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        r"""Inject the last reasoning content into assistant messages.

        For models with interleaved thinking enabled, the reasoning content
        from the model response needs to be passed back in subsequent requests
        for proper context management. This is especially important when using
        tools with interleaved thinking.

        Args:
            messages: The original messages list.

        Returns:
            Messages with reasoning content added to the last assistant
            message that has tool_calls.
        """
        if not self._last_reasoning or not self._is_thinking_enabled():
            return messages

        # Find the last assistant message with tool_calls and inject
        # reasoning content
        processed: List[OpenAIMessage] = []
        reasoning_injected = False

        for msg in reversed(messages):
            if (
                not reasoning_injected
                and isinstance(msg, dict)
                and msg.get("role") == "assistant"
                and msg.get("tool_calls")
                and self._reasoning_field not in msg
            ):
                # Inject reasoning content into this message
                new_msg = dict(msg)
                new_msg[self._reasoning_field] = self._last_reasoning
                processed.append(new_msg)  # type: ignore[arg-type]
                reasoning_injected = True
            else:
                processed.append(msg)

        # Only clear after successful injection
        if reasoning_injected:
            self._last_reasoning = None

        return list(reversed(processed))

    def _prepare_thinking_config(
        self,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        r"""Prepare the request config for thinking-enabled requests.

        Removes the interleaved_thinking parameter which is only used
        internally. Subclasses can override this to add model-specific
        configuration (e.g., Minimax adds reasoning_split=True).

        Args:
            config: The request configuration dictionary.

        Returns:
            The modified configuration dictionary.
        """
        config.pop("interleaved_thinking", None)
        return config

    def run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Run inference with interleaved thinking support.

        Note:
            Interleaved thinking is not supported with stream=True. When
            streaming is enabled, reasoning content cannot be captured and
            injected into subsequent requests.
        """
        if self._is_thinking_enabled() and self.model_config_dict.get(
            "stream", False
        ):
            logger.warning(
                "Interleaved thinking is not supported with stream=True. "
                "Reasoning content cannot be captured or injected into "
                "subsequent requests."
            )
        processed_messages = self._inject_reasoning(messages)
        response = super().run(  # type: ignore[misc]
            processed_messages, response_format, tools
        )

        if isinstance(response, ChatCompletion):
            self._last_reasoning = self._extract_reasoning(response)

        return response

    async def arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Run async inference with interleaved thinking support.

        Note:
            Interleaved thinking is not supported with stream=True. When
            streaming is enabled, reasoning content cannot be captured and
            injected into subsequent requests.
        """
        if self._is_thinking_enabled() and self.model_config_dict.get(
            "stream", False
        ):
            logger.warning(
                "Interleaved thinking is not supported with stream=True. "
                "Reasoning content cannot be captured or injected into "
                "subsequent requests."
            )
        processed_messages = self._inject_reasoning(messages)
        response = await super().arun(  # type: ignore[misc]
            processed_messages, response_format, tools
        )

        if isinstance(response, ChatCompletion):
            self._last_reasoning = self._extract_reasoning(response)

        return response
