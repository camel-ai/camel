import pytest

from camel.agents.tool_agent import HuggingFaceToolAgent, ToolAgent
from camel.utils import openai_api_key_required


def test_tool_agent_initialization():
    tool_agent = ToolAgent("tool_agent", "description")
    assert tool_agent.name == "tool_agent"
    assert tool_agent.description == "description"


@pytest.mark.slow
@pytest.mark.full_test_only
@openai_api_key_required
def test_hugging_face_tool_agent_initialization():
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    assert agent.name == "hugging_face_tool_agent"
    assert agent.remote is True
    assert agent.description.startswith(f"The `{agent.name}` is a tool agent")


@pytest.mark.slow
@pytest.mark.full_test_only
@openai_api_key_required
def test_hugging_face_tool_agent_run():
    from PIL.PngImagePlugin import PngImageFile
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    result = agent.run("Generate an image of a boat in the water")
    assert isinstance(result, PngImageFile)


@pytest.mark.slow
@pytest.mark.full_test_only
@openai_api_key_required
def test_hugging_face_tool_agent_chat():
    from PIL.PngImagePlugin import PngImageFile
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    result = agent.chat("Show me an image of a capybara")
    assert isinstance(result, PngImageFile)


@pytest.mark.slow
@pytest.mark.full_test_only
@openai_api_key_required
def test_hugging_face_tool_agent_reset():
    agent = HuggingFaceToolAgent("hugging_face_tool_agent")
    agent.reset()
