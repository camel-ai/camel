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
from typing import List, Tuple

from pydantic import BaseModel

from camel.logger import get_logger
from camel.memories.base import BaseContextCreator
from camel.memories.records import ContextRecord
from camel.messages import OpenAIMessage
from camel.utils import BaseTokenCounter

logger = get_logger(__name__)


class _ContextUnit(BaseModel):
    idx: int
    record: ContextRecord
    num_tokens: int


class ScoreBasedContextCreator(BaseContextCreator):
    r"""A default implementation of context creation strategy, which inherits
    from :obj:`BaseContextCreator`.

    This class provides a strategy to generate a conversational context from
    a list of chat history records while ensuring the total token count of
    the context does not exceed a specified limit. It prunes messages based
    on their score if the total token count exceeds the limit.

    Args:
        token_counter (BaseTokenCounter): An instance responsible for counting
            tokens in a message.
        token_limit (int): The maximum number of tokens allowed in the
            generated context.
        skip_token_counting (bool, optional): If True, token counting will be
            skipped and all messages will be included in the context. Defaults
            to True.
    """

    def __init__(
        self,
        token_counter: BaseTokenCounter,
        token_limit: int,
        skip_token_counting: bool = True,
    ) -> None:
        self._token_counter = token_counter
        self._token_limit = token_limit
        self._skip_token_counting = skip_token_counting

    @property
    def token_counter(self) -> BaseTokenCounter:
        return self._token_counter

    @property
    def token_limit(self) -> int:
        return self._token_limit

    @property
    def skip_token_counting(self) -> bool:
        return self._skip_token_counting

    def create_context(
        self,
        records: List[ContextRecord],
    ) -> Tuple[List[OpenAIMessage], int]:
        r"""Creates conversational context from chat history while respecting
        token limits.

        Constructs the context from provided records and ensures that the total
        token count does not exceed the specified limit by pruning the least
        score messages if necessary. If skip_token_counting is True, all
        messages will be included without token counting.

        Args:
            records (List[ContextRecord]): A list of message records from which
                to generate the context.

        Returns:
            Tuple[List[OpenAIMessage], int]: A tuple containing the constructed
                context in OpenAIMessage format and the total token count (or
                -1 if token counting is skipped).

        Raises:
            RuntimeError: If it's impossible to create a valid context without
                exceeding the token limit.
        """
        # Create unique context units list
        uuid_set = set()
        context_units = []
        for idx, record in enumerate(records):
            if record.memory_record.uuid not in uuid_set:
                uuid_set.add(record.memory_record.uuid)

                # Skip token counting if specified
                num_tokens = -1
                if not self.skip_token_counting:
                    num_tokens = self.token_counter.count_tokens_from_messages(
                        [record.memory_record.to_openai_message()]
                    )

                context_units.append(
                    _ContextUnit(
                        idx=idx,
                        record=record,
                        num_tokens=num_tokens,
                    )
                )

        # If token counting is skipped, return all messages
        if self.skip_token_counting:
            return self._create_output(context_units, skip_counting=True)

        # TODO: optimize the process, may give information back to memory

        # If not exceed token limit, simply return
        total_tokens = sum([unit.num_tokens for unit in context_units])
        if total_tokens <= self.token_limit:
            return self._create_output(context_units)

        # Log warning about token limit being exceeded
        logger.warning(
            f"Token limit reached ({total_tokens} > {self.token_limit}). "
            f"Some messages will be pruned from memory to meet the limit."
        )

        # Sort by score
        context_units = sorted(
            context_units, key=lambda unit: unit.record.score
        )

        # Remove the least score messages until total token number is smaller
        # than token limit
        truncate_idx = None
        for i, unit in enumerate(context_units):
            if unit.record.score == 1:
                raise RuntimeError(
                    "Cannot create context: exceed token limit.", total_tokens
                )
            total_tokens -= unit.num_tokens
            if total_tokens <= self.token_limit:
                truncate_idx = i
                break
        if truncate_idx is None:
            raise RuntimeError(
                "Cannot create context: exceed token limit.", total_tokens
            )
        return self._create_output(context_units[truncate_idx + 1 :])

    def _create_output(
        self, context_units: List[_ContextUnit], skip_counting: bool = False
    ) -> Tuple[List[OpenAIMessage], int]:
        r"""Helper method to generate output from context units.

        This method converts the provided context units into a format suitable
        for output, specifically a list of OpenAIMessages and an integer
        representing the total token count.

        Args:
            context_units: List of context units to convert to output format.
            skip_counting: If True, returns -1 as token count.
        """
        context_units = sorted(context_units, key=lambda unit: unit.idx)
        messages = [
            unit.record.memory_record.to_openai_message()
            for unit in context_units
        ]

        if skip_counting:
            return messages, -1

        return messages, sum([unit.num_tokens for unit in context_units])
