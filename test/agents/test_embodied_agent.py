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
import binascii

import pytest
import requests

from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.models import FakeLLMModel
from camel.types import ModelType, RoleType


@pytest.mark.skip(reason="Wait huggingface to update openaiv1")
@pytest.mark.model_backend
def test_get_action_space_prompt():
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT),
    )
    agent = EmbodiedAgent(
        sys_msg, tool_agents=[HuggingFaceToolAgent("hugging_face_tool_agent")]
    )
    assert "hugging_face_tool_agent" in agent.get_tool_agent_names()


@pytest.mark.skip(reason="Wait huggingface to update openaiv1")
@pytest.mark.model_backend
@pytest.mark.very_slow
def test_step(call_count=3):
    # Create an embodied agent
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT),
    )
    embodied_agent = EmbodiedAgent(
        sys_msg,
        verbose=True,
        model=FakeLLMModel(model_type=ModelType.DEFAULT),
    )
    user_msg = BaseMessage.make_user_message(
        role_name=role_name,
        content="Draw all the Camelidae species.",
    )
    for i in range(call_count):
        try:
            response = embodied_agent.step(user_msg)
        except (binascii.Error, requests.exceptions.ConnectionError) as ex:
            print(
                f"Error in calling round {i+1} "
                "Warning: caught an exception, ignoring it since "
                f"it is a known issue of Huggingface ({ex!s})"
            )
            return
        assert isinstance(
            response.msg, BaseMessage
        ), f"Error in calling round {i+1}"
        assert not response.terminated, f"Error in calling round {i+1}"
        assert isinstance(response.info, dict), f"Error in calling round {i+1}"
