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
# ============================================================================

import pytest

from camel.toolkits import ThinkingToolkit


@pytest.fixture
def thinking_toolkit():
    r"""Create a ThinkingToolkit instance for testing."""
    return ThinkingToolkit()


def test_toolkit_initialization(thinking_toolkit):
    r"""Test if the toolkit is initialized correctly."""
    assert hasattr(thinking_toolkit, 'thoughts')
    assert isinstance(thinking_toolkit.thoughts, list)
    assert len(thinking_toolkit.thoughts) == 0


def test_get_tools(thinking_toolkit):
    r"""Test getting available tools from ThinkingToolkit."""
    tools = thinking_toolkit.get_tools()
    assert len(tools) == 1
    assert tools[0].get_function_name() == "think"


def test_think_method(thinking_toolkit):
    r"""Test the think method."""
    thought = "This is a test thought"
    result = thinking_toolkit.think(thought)

    assert isinstance(result, str)
    assert "Thoughts:" in result
    assert thought in result
    assert len(thinking_toolkit.thoughts) == 1
    assert thinking_toolkit.thoughts[0] == thought


def test_multiple_thoughts(thinking_toolkit):
    r"""Test recording multiple thoughts."""
    thoughts = ["First thought", "Second thought", "Third thought"]

    for thought in thoughts:
        result = thinking_toolkit.think(thought)
        assert thought in result

    assert len(thinking_toolkit.thoughts) == len(thoughts)
    for thought in thoughts:
        assert thought in thinking_toolkit.thoughts


def test_empty_thought(thinking_toolkit):
    r"""Test handling of empty thought."""
    result = thinking_toolkit.think("")
    assert isinstance(result, str)
    assert len(thinking_toolkit.thoughts) == 1


if __name__ == "__main__":
    pytest.main([__file__])
