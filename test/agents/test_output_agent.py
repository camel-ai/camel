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

from camel.agents.output_agent import OutputAgent


@pytest.fixture
def agent():
    content = "Sample content for testing."
    return OutputAgent(content)


def test_construct_task_prompt(agent):
    messages = agent._construct_task_prompt()
    expected_messages = [{
        "role":
        "system",
        "content":
        "You are a helpful assistant to re-organize information "
        "into a detailed instruction, below is the content for you:"
        "\nSample content for testing."
    }, {
        "role":
        "user",
        "content":
        "Please extract the detailed action information from"
        "the provided content, "
        "make it useful for a human to follow the detailed"
        "instruction step by step to solve the task."
    }]
    assert messages == expected_messages
