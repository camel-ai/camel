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
from typing import List

import pytest

from camel.messages import BaseMessage
from camel.terminators import ResponseWordsTerminator
from camel.types import RoleType, TerminationMode

NUM_TIMES = 2


def _create_messages() -> List[BaseMessage]:
    messages = []
    for _ in range(3):
        message = BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict={},
            content="GoodBye",
        )
        messages.append(message)
    return messages


@pytest.mark.parametrize('mode', [TerminationMode.ANY, TerminationMode.ALL])
def test_response_words_termination(mode):
    words_dict = {
        "goodbye": NUM_TIMES,
        "good bye": NUM_TIMES,
        "thank": NUM_TIMES,
        "bye": NUM_TIMES,
        "welcome": NUM_TIMES,
        "language model": NUM_TIMES + 1,
    }
    termination = ResponseWordsTerminator(words_dict=words_dict, mode=mode)
    messages = _create_messages()
    terminated, termination_reason = termination.is_terminated(messages)
    assert not terminated
    assert termination_reason is None
    messages = _create_messages()
    terminated, termination_reason = termination.is_terminated(messages)
    if mode == TerminationMode.ANY:
        assert terminated
        assert "goodbye" in termination_reason
    if mode == TerminationMode.ALL:
        assert not terminated
        assert termination_reason is None
    termination.reset()
    assert not termination._terminated
    assert termination._termination_reason is None
