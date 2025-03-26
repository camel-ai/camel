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

from camel.toolkits import ThinkingToolkit


@pytest.fixture
def thinking_toolkit():
    r"""Create a ThinkingToolkit instance for testing."""
    return ThinkingToolkit()


def test_toolkit_initialization(thinking_toolkit):
    r"""Test if the toolkit is initialized correctly."""
    assert hasattr(thinking_toolkit, 'plans')
    assert hasattr(thinking_toolkit, 'hypotheses')
    assert hasattr(thinking_toolkit, 'thoughts')
    assert hasattr(thinking_toolkit, 'contemplations')
    assert hasattr(thinking_toolkit, 'critiques')
    assert hasattr(thinking_toolkit, 'syntheses')
    assert hasattr(thinking_toolkit, 'reflections')

    assert all(
        isinstance(attr, list)
        for attr in [
            thinking_toolkit.plans,
            thinking_toolkit.hypotheses,
            thinking_toolkit.thoughts,
            thinking_toolkit.contemplations,
            thinking_toolkit.critiques,
            thinking_toolkit.syntheses,
            thinking_toolkit.reflections,
        ]
    )

    assert all(
        len(attr) == 0
        for attr in [
            thinking_toolkit.plans,
            thinking_toolkit.hypotheses,
            thinking_toolkit.thoughts,
            thinking_toolkit.contemplations,
            thinking_toolkit.critiques,
            thinking_toolkit.syntheses,
            thinking_toolkit.reflections,
        ]
    )


def test_get_tools(thinking_toolkit):
    r"""Test getting available tools from ThinkingToolkit."""
    tools = thinking_toolkit.get_tools()
    assert len(tools) == 7
    tool_names = {tool.get_function_name() for tool in tools}
    assert tool_names == {
        "plan",
        "hypothesize",
        "think",
        "contemplate",
        "critique",
        "synthesize",
        "reflect",
    }


def test_plan_method(thinking_toolkit):
    r"""Test the plan method."""
    plan = "This is a test plan"
    result = thinking_toolkit.plan(plan)

    assert isinstance(result, str)
    assert "Plan:" in result
    assert plan in result
    assert len(thinking_toolkit.plans) == 1
    assert thinking_toolkit.plans[0] == plan


def test_hypothesize_method(thinking_toolkit):
    r"""Test the hypothesize method."""
    # Should suggest making a plan first
    hypothesis = "Test hypothesis"
    result = thinking_toolkit.hypothesize(hypothesis)
    assert "plan" in result.lower()

    # After making a plan
    thinking_toolkit.plan("Test plan")
    result = thinking_toolkit.hypothesize(hypothesis)
    assert "Hypothesis:" in result
    assert hypothesis in result
    assert len(thinking_toolkit.hypotheses) == 1
    assert thinking_toolkit.hypotheses[0] == hypothesis


def test_think_method(thinking_toolkit):
    r"""Test the think method."""
    # Should suggest making a plan first
    thought = "Test thought"
    result = thinking_toolkit.think(thought)
    assert "plan" in result.lower()

    # After making a plan
    thinking_toolkit.plan("Test plan")
    result = thinking_toolkit.think(thought)
    assert "Thought:" in result
    assert thought in result
    assert len(thinking_toolkit.thoughts) == 1
    assert thinking_toolkit.thoughts[0] == thought


def test_contemplate_method(thinking_toolkit):
    r"""Test the contemplate method."""
    # Should suggest thinking first
    contemplation = "Test contemplation"
    result = thinking_toolkit.contemplate(contemplation)
    assert "think" in result.lower()

    # After planning and thinking
    thinking_toolkit.plan("Test plan")
    thinking_toolkit.think("Test thought")
    result = thinking_toolkit.contemplate(contemplation)
    assert "Contemplation:" in result
    assert contemplation in result
    assert len(thinking_toolkit.contemplations) == 1
    assert thinking_toolkit.contemplations[0] == contemplation


def test_critique_method(thinking_toolkit):
    r"""Test the critique method."""
    critique = "Test critique"
    result = thinking_toolkit.critique(critique)
    assert "contemplat" in result.lower()

    # After proper setup
    thinking_toolkit.plan("Test plan")
    thinking_toolkit.think("Test thought")
    thinking_toolkit.contemplate("Test contemplation")
    result = thinking_toolkit.critique(critique)
    assert "Critique:" in result
    assert critique in result
    assert len(thinking_toolkit.critiques) == 1
    assert thinking_toolkit.critiques[0] == critique


def test_synthesize_method(thinking_toolkit):
    r"""Test the synthesize method."""
    # Should suggest critiquing first
    synthesis = "Test synthesis"
    result = thinking_toolkit.synthesize(synthesis)
    assert "critiquing" in result.lower()

    # After proper setup
    thinking_toolkit.plan("Test plan")
    thinking_toolkit.think("Test thought")
    thinking_toolkit.contemplate("Test contemplation")
    thinking_toolkit.critique("Test critique")
    result = thinking_toolkit.synthesize(synthesis)
    assert "Synthesis:" in result
    assert synthesis in result
    assert len(thinking_toolkit.syntheses) == 1
    assert thinking_toolkit.syntheses[0] == synthesis


def test_reflect_method(thinking_toolkit):
    r"""Test the reflect method."""
    # Should suggest synthesizing first
    reflection = "Test reflection"
    result = thinking_toolkit.reflect(reflection)
    assert "synthesiz" in result.lower()

    # After proper setup
    thinking_toolkit.plan("Test plan")
    thinking_toolkit.think("Test thought")
    thinking_toolkit.contemplate("Test contemplation")
    thinking_toolkit.critique("Test critique")
    thinking_toolkit.synthesize("Test synthesis")
    result = thinking_toolkit.reflect(reflection)
    assert "Reflection:" in result
    assert reflection in result
    assert len(thinking_toolkit.reflections) == 1
    assert thinking_toolkit.reflections[0] == reflection


def test_empty_inputs(thinking_toolkit):
    r"""Test handling of empty inputs."""
    thinking_toolkit.plan("Test plan")  # Setup prerequisite

    result = thinking_toolkit.think("")
    assert isinstance(result, str)
    assert len(thinking_toolkit.thoughts) == 1


if __name__ == "__main__":
    pytest.main([__file__])
