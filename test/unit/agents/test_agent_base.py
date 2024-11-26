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
import pytest

from camel.agents import BaseAgent


class DummyAgent(BaseAgent):
    def __init__(self):
        self.step_count = 0

    def reset(self):
        self.step_count = 0

    def step(self):
        self.step_count += 1


def test_base_agent():
    with pytest.raises(TypeError):
        BaseAgent()


def test_dummy_agent():
    agent = DummyAgent()
    assert agent.step_count == 0
    agent.step()
    assert agent.step_count == 1
    agent.reset()
    assert agent.step_count == 0
    agent.step()
    assert agent.step_count == 1
    agent.step()
    assert agent.step_count == 2
