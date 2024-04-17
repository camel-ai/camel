from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.types import RoleType

import binascii
import pytest
import requests
from mock import patch
from camel.agents import ChatAgent
from camel.agents.react_embodied_agent import ReactAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.types import RoleType
import pdb


@patch.object(ChatAgent, 'step')
def test_react_agent(mock_step):
    mock_content = generate_mock_content()
    mock_msg = BaseMessage(role_name="Reactive Agent",
                           role_type=RoleType.ASSISTANT, meta_dict=None,
                           content=mock_content)

    # Mock the step function
    mock_step.return_value = ChatAgentResponse(msgs=[mock_msg],
                                               terminated=False, info={})

    model_config_description = ChatGPTConfig()

    # Construct reactive reasoner agent
    model_type = None

    react_agent = (ReactAgent(
        model_type=model_type, model_config=model_config_description))

    # Generate the conditions and quality dictionary based on the mock step
    # function
    react_reasoning = (
        react_agent.re_act_reasoning())

    expected_dict = generate_expected_content()
    assert react_reasoning == expected_dict
    pdb.set_trace()

# Generate mock content for the deductive reasoner agent
def generate_mock_content():
    return """
    I want to minimize a Booth function without knowing its explicit expression.
    """  # noqa: E501


# Generate expected dictionary of conditions and quality
def generate_expected_content():
    return {'Thought': 'Based on the keyword optimization, we could implement the optimization tool agent concerning {func_name} with limited information.' ,
            'instruction': 'You are trying to minimize the output (y) of a function by choosing input (x). '
                           'The goal is to choose x such that y is as small as possible.\n\nYou get to observe y once you choose the value of x, where x is a 2-dimensional vector.'
                           '\nThis means x = [x1, x2], where x1 and x2 are real numbers.\n\n\nThe range of x1 and x2 is [-10, 10].\n'
                           'Please do not choose x outside of this range.\n\nChoose x within 10 attempts.\nYou can choose to stop at any time.'
                           '\n\nOutput format:\nx = [x1, x2]',
            'observation': 'x=[6.61, 6.81]\nFunction outputs y = 400.9338\nYou have 10 attempts left!\n'
                           'Please output the next x that will make this function output the smallest y.\nFormat: x = [x1, x2]\nOutput:',
            'feedback': None}
