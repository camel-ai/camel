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
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from camel.logger import get_logger
from camel.memories.base import BaseContextCreator
from camel.memories.records import ContextRecord
from camel.messages import OpenAIMessage
from camel.types.enums import OpenAIBackendRole
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
        r"""Constructs conversation context from chat history while respecting
        token limits.

        Key strategies:
        1. System message is always prioritized and preserved
        2. Truncation removes low-score messages first
        3. Final output maintains chronological order and in history memory,
           the score of each message decreases according to keep_rate. The
           newer the message, the higher the score.
        4. Tool calls and their responses are kept together to maintain
           API compatibility

        Args:
            records (List[ContextRecord]): List of context records with scores
                and timestamps.

        Returns:
            Tuple[List[OpenAIMessage], int]:
            - Ordered list of OpenAI messages
            - Total token count of the final context

        Raises:
            RuntimeError: If system message alone exceeds token limit
        """
        # ======================
        # 1. System Message Handling
        # ======================
        system_unit, regular_units = self._extract_system_message(records)
        system_tokens = system_unit.num_tokens if system_unit else 0

        # Check early if system message alone exceeds token limit
        if system_tokens > self.token_limit:
            raise RuntimeError(
                f"System message alone exceeds token limit"
                f": {system_tokens} > {self.token_limit}",
                system_tokens,
            )

        # ======================
        # 2. Deduplication & Initial Processing
        # ======================
        seen_uuids = set()
        if system_unit:
            seen_uuids.add(system_unit.record.memory_record.uuid)

        # Process non-system messages with deduplication
        for idx, record in enumerate(records):
            if record.memory_record.uuid in seen_uuids:
                continue
            seen_uuids.add(record.memory_record.uuid)

            token_count = self.token_counter.count_tokens_from_messages(
                [record.memory_record.to_openai_message()]
            )
            regular_units.append(
                _ContextUnit(
                    idx=idx,
                    record=record,
                    num_tokens=token_count,
                )
            )

        # ======================
        # 3. Tool Call Relationship Mapping
        # ======================
        tool_call_groups = self._group_tool_calls_and_responses(regular_units)

        # ======================
        # 4. Token Calculation
        # ======================
        total_tokens = system_tokens + sum(u.num_tokens for u in regular_units)

        # ======================
        # 5. Early Return if Within Limit
        # ======================
        if total_tokens <= self.token_limit:
            sorted_units = sorted(
                regular_units, key=self._conversation_sort_key
            )
            return self._assemble_output(sorted_units, system_unit)

        # ======================
        # 6. Truncation Logic with Tool Call Awareness
        # ======================
        logger.warning(
            f"Context truncation required "
            f"({total_tokens} > {self.token_limit}), "
            f"pruning low-score messages."
        )

        remaining_units = self._truncate_with_tool_call_awareness(
            regular_units, tool_call_groups, system_tokens
        )

        # ======================
        # 7. Output Assembly
        # ======================

        # In case system message is the only message in memory when sorted
        # units are empty, raise an error
        if system_unit and len(remaining_units) == 0 and len(records) > 1:
            raise RuntimeError(
                "System message and current message exceeds token limit ",
                total_tokens,
            )

        # Sort remaining units chronologically
        final_units = sorted(remaining_units, key=self._conversation_sort_key)
        return self._assemble_output(final_units, system_unit)

    def _group_tool_calls_and_responses(
        self, units: List[_ContextUnit]
    ) -> Dict[str, List[_ContextUnit]]:
        r"""Groups tool calls with their corresponding responses.

        Args:
            units (List[_ContextUnit]): List of context units to analyze

        Returns:
            Dict[str, List[_ContextUnit]]: Mapping from tool_call_id to list of
                related units (tool call + responses)
        """
        tool_call_groups: Dict[str, List[_ContextUnit]] = {}

        for unit in units:
            message = unit.record.memory_record.message
            backend_role = unit.record.memory_record.role_at_backend

            # Check if this is a tool call message
            if hasattr(message, 'func_name') and hasattr(
                message, 'tool_call_id'
            ):
                tool_call_id = getattr(message, 'tool_call_id', None)
                if tool_call_id:
                    if tool_call_id not in tool_call_groups:
                        tool_call_groups[tool_call_id] = []
                    tool_call_groups[tool_call_id].append(unit)

            # Check if this is a tool response message
            elif backend_role == OpenAIBackendRole.FUNCTION:
                tool_call_id = None
                if hasattr(message, 'tool_call_id'):
                    tool_call_id = getattr(message, 'tool_call_id', None)
                elif hasattr(message, 'result') and hasattr(
                    message, 'tool_call_id'
                ):
                    tool_call_id = getattr(message, 'tool_call_id', None)

                if tool_call_id:
                    if tool_call_id not in tool_call_groups:
                        tool_call_groups[tool_call_id] = []
                    tool_call_groups[tool_call_id].append(unit)

        return tool_call_groups

    def _truncate_with_tool_call_awareness(
        self,
        regular_units: List[_ContextUnit],
        tool_call_groups: Dict[str, List[_ContextUnit]],
        system_tokens: int,
    ) -> List[_ContextUnit]:
        r"""Truncates messages while preserving tool call-response pairs.

        Args:
            regular_units (List[_ContextUnit]): All regular message units
            tool_call_groups (Dict[str, List[_ContextUnit]]): Grouped tool
                calls
            system_tokens (int): Tokens used by system message

        Returns:
            List[_ContextUnit]: Units that fit within token limit
        """
        # Create sets for quick lookup of tool call related units
        tool_call_unit_ids = set()
        for group in tool_call_groups.values():
            for unit in group:
                tool_call_unit_ids.add(unit.record.memory_record.uuid)

        # Separate tool call groups and standalone units
        standalone_units = [
            u
            for u in regular_units
            if u.record.memory_record.uuid not in tool_call_unit_ids
        ]

        # Sort standalone units for truncation (high scores first)
        standalone_units.sort(key=self._truncation_sort_key)

        # Sort tool call groups by their best (highest) score
        sorted_tool_groups = []
        for _tool_call_id, group in tool_call_groups.items():
            # Use the highest score in the group as the group's score
            best_score = max(unit.record.score for unit in group)
            latest_timestamp = max(unit.record.timestamp for unit in group)
            group_tokens = sum(unit.num_tokens for unit in group)
            sorted_tool_groups.append(
                ((-best_score, -latest_timestamp), group, group_tokens)
            )

        sorted_tool_groups.sort(key=lambda x: x[0])

        # Greedy selection to fit within token limit
        remaining_units = []
        current_tokens = system_tokens

        # First, try to include complete tool call groups
        for _, group, group_tokens in sorted_tool_groups:
            if current_tokens + group_tokens <= self.token_limit:
                remaining_units.extend(group)
                current_tokens += group_tokens

        # Then, include standalone units
        for unit in standalone_units:
            if current_tokens + unit.num_tokens <= self.token_limit:
                remaining_units.append(unit)
                current_tokens += unit.num_tokens

        return remaining_units

    def _extract_system_message(
        self, records: List[ContextRecord]
    ) -> Tuple[Optional[_ContextUnit], List[_ContextUnit]]:
        r"""Extracts the system message from records and validates it.

        Args:
            records (List[ContextRecord]): List of context records
                representing conversation history.

        Returns:
            Tuple[Optional[_ContextUnit], List[_ContextUnit]]: containing:
            - The system message as a `_ContextUnit`, if valid; otherwise,
                `None`.
            - An empty list, serving as the initial container for regular
                messages.
        """
        if not records:
            return None, []

        first_record = records[0]
        if (
            first_record.memory_record.role_at_backend
            != OpenAIBackendRole.SYSTEM
        ):
            return None, []

        message = first_record.memory_record.to_openai_message()
        tokens = self.token_counter.count_tokens_from_messages([message])
        system_message_unit = _ContextUnit(
            idx=0,
            record=first_record,
            num_tokens=tokens,
        )
        return system_message_unit, []

    def _truncation_sort_key(self, unit: _ContextUnit) -> Tuple[float, float]:
        r"""Defines the sorting key for the truncation phase.

        Sorting priority:
        - Primary: Sort by score in descending order (higher scores first).
        - Secondary: Sort by timestamp in ascending order (older messages
            first when scores are equal).

        Args:
            unit (_ContextUnit): A `_ContextUnit` representing a conversation
                record.

        Returns:
            Tuple[float, float]:
            - Negative score for descending order sorting.
            - Timestamp for ascending order sorting.
        """
        return (-unit.record.score, unit.record.timestamp)

    def _conversation_sort_key(
        self, unit: _ContextUnit
    ) -> Tuple[float, float]:
        r"""Defines the sorting key for assembling the final output.

        Sorting priority:
        - Primary: Sort by timestamp in ascending order (chronological order).
        - Secondary: Sort by score in descending order (higher scores first
            when timestamps are equal).

        Args:
            unit (_ContextUnit): A `_ContextUnit` representing a conversation
                record.

        Returns:
            Tuple[float, float]:
            - Timestamp for chronological sorting.
            - Negative score for descending order sorting.
        """
        return (unit.record.timestamp, -unit.record.score)

    def _assemble_output(
        self,
        context_units: List[_ContextUnit],
        system_unit: Optional[_ContextUnit],
    ) -> Tuple[List[OpenAIMessage], int]:
        r"""Assembles final message list with proper ordering and token count.

        Args:
            context_units (List[_ContextUnit]): Sorted list of regular message
                units.
            system_unit (Optional[_ContextUnit]): System message unit (if
                present).

        Returns:
            Tuple[List[OpenAIMessage], int]: Tuple of (ordered messages, total
                tokens)
        """
        messages = []
        total_tokens = 0

        # Add system message first if present
        if system_unit:
            messages.append(
                system_unit.record.memory_record.to_openai_message()
            )
            total_tokens += system_unit.num_tokens

        # Add sorted regular messages
        for unit in context_units:
            messages.append(unit.record.memory_record.to_openai_message())
            total_tokens += unit.num_tokens

        return messages, total_tokens
