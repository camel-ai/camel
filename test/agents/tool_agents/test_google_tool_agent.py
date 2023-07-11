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

from camel.agents.tool_agents import GoogleToolAgent

SA_EXPECTED = ("Saudi Arabia, officially the Kingdom of Saudi "
               "Arabia, is a country in West Asia.")


@pytest.mark.model_backend
def test_google_tool_agent_initialization():
    agent = GoogleToolAgent("google_tool_agent")

    assert agent.name == "google_tool_agent"
    assert agent.description.startswith("GoogleSearch[<keyword>]")


@pytest.mark.model_backend
def test_google_tool_agent_search_step():
    agent = GoogleToolAgent("google_tool_agent")
    result = agent.step("Saudi Arabia")

    assert isinstance(result, str)
    assert result.startswith(SA_EXPECTED)
