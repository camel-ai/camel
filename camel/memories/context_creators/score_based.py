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

from typing import List, Optional, Tuple

from camel.memories.base import BaseContextCreator
from camel.memories.records import ContextRecord
from camel.messages import OpenAIMessage
from camel.types.enums import OpenAIBackendRole
from camel.utils import BaseTokenCounter


class ScoreBasedContextCreator(BaseContextCreator):
    r"""A context creation strategy that orders records chronologically.

    This class supports token count estimation to reduce expensive repeated
    token counting. When a cached token count is available, it estimates
    new message tokens using character-based approximation instead of
    calling the token counter for every message.

    Args:
        token_counter (BaseTokenCounter): Token counter instance used to
            compute the combined token count of the returned messages.
        token_limit (int): Retained for API compatibility. No longer used to
            filter records.
    """

    def __init__(
        self, token_counter: BaseTokenCounter, token_limit: int
    ) -> None:
        self._token_counter = token_counter
        self._token_limit = token_limit
        # Token count cache: stores the known token count and corresponding
        # message count from the last LLM response
        self._cached_token_count: Optional[int] = None
        self._cached_message_count: int = 0

    @property
    def token_counter(self) -> BaseTokenCounter:
        return self._token_counter

    @property
    def token_limit(self) -> int:
        return self._token_limit

    def set_cached_token_count(
        self, token_count: int, message_count: int
    ) -> None:
        r"""Set the cached token count from LLM response usage.

        Args:
            token_count (int): The total token count (prompt + completion)
                from LLM response usage.
            message_count (int): The number of messages including the
                assistant response that will be added to memory.
        """
        self._cached_token_count = token_count
        self._cached_message_count = message_count

    def clear_cache(self) -> None:
        r"""Clear the cached token count."""
        self._cached_token_count = None
        self._cached_message_count = 0

    def _estimate_message_tokens(self, message: OpenAIMessage) -> int:
        r"""Estimate token count for a single message.

        Uses ~2 chars/token as a conservative approximation to handle both
        ASCII (~4 chars/token) and CJK text (~1-2 chars/token).

        Args:
            message: The OpenAI message to estimate.

        Returns:
            Estimated token count (intentionally conservative).
        """
        content = message.get("content", "")
        token_estimate = 4  # message overhead

        if isinstance(content, list):
            # Multimodal content
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        # Images: 85 (low) to ~1500 (high detail large image)
                        # Use 1500 as conservative estimate
                        token_estimate += 1500
                    else:
                        token_estimate += len(str(part)) // 2
                else:
                    token_estimate += len(str(part)) // 2
        else:
            token_estimate += len(str(content)) // 2

        # Add tool_calls if present (already text, safe to serialize)
        if message.get("tool_calls"):
            token_estimate += len(str(message.get("tool_calls"))) // 2

        return token_estimate

    def create_context(
        self,
        records: List[ContextRecord],
    ) -> Tuple[List[OpenAIMessage], int]:
        """Returns messages sorted by timestamp and their total token count."""

        system_record: Optional[ContextRecord] = None
        remaining_records: List[ContextRecord] = []

        for record in records:
            if (
                system_record is None
                and record.memory_record.role_at_backend
                == OpenAIBackendRole.SYSTEM
            ):
                system_record = record
                continue
            remaining_records.append(record)

        remaining_records.sort(key=lambda record: record.timestamp)

        messages: List[OpenAIMessage] = []
        if system_record is not None:
            messages.append(system_record.memory_record.to_openai_message())

        messages.extend(
            record.memory_record.to_openai_message()
            for record in remaining_records
        )

        if not messages:
            return [], 0

        current_count = len(messages)

        # Use cache if available and valid
        if (
            self._cached_token_count is not None
            and self._cached_message_count > 0
        ):
            if current_count == self._cached_message_count:
                # Same message count, use cached value directly
                return messages, self._cached_token_count
            elif current_count > self._cached_message_count:
                # New messages added, estimate incrementally
                new_messages = messages[self._cached_message_count :]
                estimated_new_tokens = sum(
                    self._estimate_message_tokens(msg) for msg in new_messages
                )
                return (
                    messages,
                    self._cached_token_count + estimated_new_tokens,
                )
            # current_count < cached: messages were removed, cache invalid

        # No cache or cache is stale - do full calculation
        total_tokens = self.token_counter.count_tokens_from_messages(messages)
        return messages, total_tokens
