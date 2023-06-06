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

from camel.agents import GorillaAgent
from camel.typing import ModelType
from camel.utils import openai_api_key_required


def test_gorilla_agent_initialization():
    agent = GorillaAgent("gorilla_agent")
    assert agent.name == "gorilla_agent"
    assert agent.gorilla_model == "gorilla-7b-hf-v0"
    assert agent.code_model == ModelType.GPT_4
    assert agent.description.startswith(
        f"The `{agent.name}` is a tool agent that")


@pytest.mark.slow
@pytest.mark.full_test_only
@openai_api_key_required
def test_gorilla_agent_step():
    agent = GorillaAgent("gorilla_agent")
    result = agent.step(
        "Generate an image of a boat in the water",
        "I would like to generate an image according to a prompt.")
    assert result is None
