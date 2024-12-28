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
from unittest.mock import MagicMock

import pytest
import requests
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.types import ChatCompletion, RoleType

model_backend_rsp_base = ChatCompletion(
    id="mock_response_id",
    choices=[
        Choice(
            finish_reason="stop",
            index=0,
            logprobs=None,
            message=ChatCompletionMessage(
                content="This is a mock response content.",
                role="assistant",
                function_call=None,
                tool_calls=None,
            ),
        )
    ],
    created=123456789,
    model="gpt-4o-2024-05-13",
    object="chat.completion",
    usage=CompletionUsage(
        completion_tokens=32,
        prompt_tokens=15,
        total_tokens=47,
    ),
)


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
def test_step(step_call_count=3):
    # Create an embodied agent
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT),
    )
    embodied_agent = EmbodiedAgent(sys_msg, verbose=True)
    embodied_agent.model_backend.run = MagicMock(
        return_value=model_backend_rsp_base
    )

    user_msg = BaseMessage.make_user_message(
        role_name=role_name,
        content="Draw all the Camelidae species.",
    )
    for i in range(step_call_count):
        try:
            response = embodied_agent.step(user_msg)
        except (binascii.Error, requests.exceptions.ConnectionError) as ex:
            print(
                "Warning: caught an exception, ignoring it since "
                f"it is a known issue of Huggingface ({ex!s})"
            )
            return
        assert isinstance(response.msg, BaseMessage), f"Error in round {i+1}"
        assert not response.terminated, f"Error in round {i+1}"
        assert isinstance(response.info, dict), f"Error in round {i+1}"
