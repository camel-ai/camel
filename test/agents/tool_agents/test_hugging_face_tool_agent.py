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

from camel.agents import HuggingFaceToolAgent


@pytest.mark.model_backend
@pytest.mark.full_test_only
def test_hugging_face_tool_agent_initialization():
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    assert agent.name == "hugging_face_tool_agent"
    assert agent.remote is True
    assert agent.description.startswith(f"The `{agent.name}` is a tool agent")


@pytest.mark.model_backend
@pytest.mark.full_test_only
def test_hugging_face_tool_agent_step():
    from PIL.PngImagePlugin import PngImageFile
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    result = agent.step("Generate an image of a boat in the water")
    assert isinstance(result, PngImageFile)


@pytest.mark.model_backend
@pytest.mark.full_test_only
def test_hugging_face_tool_agent_chat():
    from PIL.PngImagePlugin import PngImageFile
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    result = agent.chat("Show me an image of a capybara")
    assert isinstance(result, PngImageFile)


@pytest.mark.model_backend
@pytest.mark.full_test_only
def test_hugging_face_tool_agent_reset():
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    agent.reset()
