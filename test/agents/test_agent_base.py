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
import pytest
from overrides import override

from camel.agents import BaseAgent, ChatAgentResponse
from camel.messages import BaseMessage
from camel.typing import RoleType


class DummyAgent(BaseAgent):

    def __init__(self):
        self.step_count = 0

    @override
    def reset(self) -> None:
        self.step_count = 0

    @override
    def step(
        self,
        input_message: BaseMessage,
    ) -> ChatAgentResponse:
        self.step_count += 1
        return ChatAgentResponse([], False, {})


def test_base_agent():
    with pytest.raises(TypeError):
        BaseAgent()


def test_dummy_agent():
    agent = DummyAgent()
    input_message: BaseMessage = BaseMessage("foo role", RoleType.USER, None,
                                             "content string")
    assert agent.step_count == 0
    agent.step(input_message)
    assert agent.step_count == 1
    agent.reset()
    assert agent.step_count == 0
    agent.step(input_message)
    assert agent.step_count == 1
    agent.step(input_message)
    assert agent.step_count == 2
