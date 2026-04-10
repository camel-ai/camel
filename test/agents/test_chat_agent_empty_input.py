import pytest

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import RoleType
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


@pytest.fixture
def agent():
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    return ChatAgent(
        system_message=BaseMessage(
            role_name="assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict={},
            content="You are a helpful assistant.",
        ),
        model=model,
    )


def test_step_with_none_input(agent):
    """ChatAgent.step should not crash when input is None"""
    response = agent.step(None)

    assert response is not None
    assert response.terminated is False
    assert "error" in response.info
    assert response.info["error"] == "empty_input"


def test_step_with_empty_string(agent):
    """ChatAgent.step should handle empty string"""
    response = agent.step("")

    assert response is not None
    assert response.terminated is False
    assert "error" in response.info


def test_step_with_whitespace(agent):
    """ChatAgent.step should handle whitespace input"""
    response = agent.step("   ")

    assert response is not None
    assert response.terminated is False
    assert "error" in response.info