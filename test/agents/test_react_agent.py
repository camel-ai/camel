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

from camel.agents import ReActAgent
from camel.agents.tool_agents import GoogleToolAgent, WikiToolAgent
from camel.agents.tool_agents.wiki_tool_agent import LOOKUP_OP, SEARCH_OP
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.typing import RoleType


@pytest.mark.model_backend
def test_get_action_space_prompt():
    role_name = "Searcher"
    meta_dict = dict(role=role_name, task="Answer questions")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict, role_tuple=(role_name, RoleType.REACT))

    wiki_tool = WikiToolAgent('wiki_tool_agent')
    google_tool = GoogleToolAgent('google_tool_agent')
    action_space = {
        'GoogleSearch': google_tool,
        'WikiSearch': wiki_tool,
        'WikiLookup': wiki_tool,
    }

    react_agent = ReActAgent(
        sys_msg,
        verbose=True,
        action_space=action_space,
    )

    act_space_prompt = react_agent.get_action_space_prompt()
    assert act_space_prompt.find(SEARCH_OP) != -1
    assert act_space_prompt.find(LOOKUP_OP) != -1
    assert act_space_prompt.find("GoogleSearch[<keyword>]") != -1


@pytest.mark.model_backend
def test_step():
    # Create an embodied agent
    role_name = "Searcher"
    meta_dict = dict(role=role_name, task="Answer questions")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict, role_tuple=(role_name, RoleType.REACT))

    wiki_tool = WikiToolAgent('wiki_tool_agent')
    google_tool = GoogleToolAgent('google_tool_agent')
    action_space = {
        'GoogleSearch': google_tool,
        'WikiSearch': wiki_tool,
        'WikiLookup': wiki_tool,
    }

    react_agent = ReActAgent(
        sys_msg,
        verbose=True,
        action_space=action_space,
    )

    question = "Were Scott Derrickson and Ed Wood of the same nationality?"
    content = f"Answer the question: {question}"

    user_msg = BaseMessage.make_user_message(role_name=role_name,
                                             content=content)
    output_message, n, info = react_agent.step(user_msg)

    assert isinstance(output_message, BaseMessage)
    assert isinstance(n, int)
    assert isinstance(info, dict)
