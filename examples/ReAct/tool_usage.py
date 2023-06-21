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
from typing import Dict
from colorama import Fore

from camel.agents.ReAct_agent import ReActAgent
from camel.agents.tool_agents.base import BaseToolAgent
from camel.agents.tool_agents.wiki_tool_agent import WikiToolAgent
from camel.agents.tool_agents.google_tool_agent import GoogleToolAgent

from camel.generators import SystemMessageGenerator
from camel.messages import UserChatMessage
from camel.typing import RoleType, ModelType


def main():
    role_name = "Searcher"
    meta_dict = dict(role=role_name, task="Answer questions")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(role_name, RoleType.ASSISTANT))

    # The tool to be used should be the Wikipedia API
    # For using this
    print("Creating Tool agents...")
    wiki_tool = WikiToolAgent('wiki_tool_agent')
    google_tool = GoogleToolAgent('google_tool_agent')
    action_space = {
        'GoogleSearch': google_tool,
        'WikiSearch' : wiki_tool,
        'WikiLookup' : wiki_tool,
    }
    action_space: Dict[str, BaseToolAgent]

    print("Creating ReActAgent...")
    react_agent = ReActAgent(
        sys_msg,
        model=ModelType.GPT_3_5_TURBO,
        verbose=True,
        action_space=action_space,
    )

    print("Passing message into the ReActAgent...")
    # question = "Were Scott Derrickson and Ed Wood of the same nationality?"
    # question = "What female sports league does the oldest football association in Africa includes?"
    question = "Within which sports complex is this sports facility located where 1990 FIFA World Cup Final between West Germany and Argentina took place?"
    user_msg = UserChatMessage(
        role_name=role_name, 
        content=(
            f"Answer the question: {question}"
        ))
    output_message, _, _ = react_agent.step(user_msg)
    # print(output_message.content)


if __name__ == '__main__':
    main()
