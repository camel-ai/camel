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

from typing import List, Optional, Tuple

from camel.memories.base import BaseContextCreator
from camel.memories.records import ContextRecord
from camel.messages import OpenAIMessage
from camel.types.enums import OpenAIBackendRole
from camel.utils import BaseTokenCounter


class ScoreBasedContextCreator(BaseContextCreator):
    r"""A context creation strategy that orders records chronologically.

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

    @property
    def token_counter(self) -> BaseTokenCounter:
        return self._token_counter

    @property
    def token_limit(self) -> int:
        return self._token_limit

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

        total_tokens = self.token_counter.count_tokens_from_messages(messages)
        return messages, total_tokens
