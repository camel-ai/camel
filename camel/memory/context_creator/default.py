# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from dataclasses import dataclass
from typing import List

from camel.memory.context_creator.base import BaseContextCreator
from camel.memory.memory_record import ContextRecord
from camel.messages import OpenAIMessage
from camel.utils.token_counting import BaseTokenCounter


@dataclass(frozen=True)
class _ContextUnit():
    idx: int
    record: ContextRecord
    token_num: int


class DefaultContextCreator(BaseContextCreator):

    def __init__(self, token_counter: BaseTokenCounter,
                 token_limit: int) -> None:
        self._token_counter = token_counter
        self._token_limit = token_limit

    @property
    def token_counter(self) -> BaseTokenCounter:
        return self._token_counter

    @property
    def token_limit(self) -> int:
        return self._token_limit

    def create_context(self,
                       records: List[ContextRecord]) -> List[OpenAIMessage]:
        context_units = [
            _ContextUnit(
                idx,
                r,
                self.token_counter.count_tokens_from_messages(
                    [r.m_record.to_openai_message()]),
            ) for idx, r in enumerate(records)
        ]
        # TODO: optimize the process, may give information back to memory

        # If not exceed token limit, simply return
        total_tokens = sum([unit.token_num for unit in context_units])
        if total_tokens <= self.token_limit:
            return self._create_output(context_units)

        # Sort by importance
        context_units = sorted(context_units,
                               key=lambda unit: unit.record.importance)

        # Remove messages until total token number < token limit
        flag = None
        for i, unit in enumerate(context_units):
            if unit.record.importance == 1:
                raise RuntimeError(
                    "Cannot create context: exceed token limit.")
            total_tokens -= unit.token_num
            if total_tokens <= self.token_limit:
                flag = i
                break
        if flag is None:
            raise RuntimeError("Cannot create context: exceed token limit.")
        return self._create_output(context_units[flag + 1:])

    def _create_output(
            self, context_units: List[_ContextUnit]) -> List[OpenAIMessage]:
        context_units = sorted(context_units, key=lambda unit: unit.idx)
        return [
            unit.record.m_record.to_openai_message() for unit in context_units
        ]
