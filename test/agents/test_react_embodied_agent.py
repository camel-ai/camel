from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.types import RoleType, ReasonType
from camel.functions.search_functions import *

import binascii
import pytest
import requests

@pytest.mark.skip(reason="Wait huggingface to update openaiv1")
@pytest.mark.model_backend
def test_get_action_space_prompt():
    role_name = "Reasoning Agent"
    meta_dict = dict(role=role_name, task="Reasoning")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT))
    agent = EmbodiedAgent(
        sys_msg, tool_agents=[HuggingFaceToolAgent('hugging_face_tool_agent')])
    assert 'hugging_face_tool_agent' in agent.get_tool_agent_names()


@pytest.mark.skip(reason="Wait huggingface to update openaiv1")
@pytest.mark.model_backend
@pytest.mark.very_slow
def test_step():
    # Create an embodied agent
    role_name = "Reasoning Agent"
    meta_dict = dict(role=role_name, task="Reasoning")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT))
    embodied_agent = EmbodiedAgent(sys_msg, verbose=True)
    user_msg = BaseMessage.make_user_message(
        role_name=role_name,
        content="Find out who is the best.",
    )
    try:
        response = embodied_agent.step(user_msg)
    except (binascii.Error, requests.exceptions.ConnectionError) as ex:
        print("Warning: caught an exception, ignoring it since "
              f"it is a known issue of Huggingface ({str(ex)})")
        return
    assert isinstance(response.msg, BaseMessage)
    assert not response.terminated
    assert isinstance(response.info, dict)