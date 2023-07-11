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

from camel.agents import ReActAgent
from camel.agents.tool_agents import (
    BaseToolAgent,
    GoogleToolAgent,
    WikiToolAgent,
)
from camel.generators import SystemMessageGenerator
from camel.messages import BaseMessage
from camel.typing import ModelType, RoleType


def main(model=ModelType.GPT_4):
    role_name = "Searcher"
    meta_dict = dict(role=role_name, task="Answer questions")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict, role_tuple=(role_name, RoleType.REACT))

    # The tool to be used should be the Wikipedia API
    print("Creating Tool agents...")
    wiki_tool = WikiToolAgent('wiki_tool_agent')
    google_tool = GoogleToolAgent('google_tool_agent')
    action_space = {
        'GoogleSearch': google_tool,
        'WikiSearch': wiki_tool,
        'WikiLookup': wiki_tool,
    }
    action_space: Dict[str, BaseToolAgent]

    print("Creating ReActAgent...")
    react_agent = ReActAgent(
        sys_msg,
        model=model,
        verbose=True,
        action_space=action_space,
    )

    print("Passing message into the ReActAgent...")
    question = ("Within which sports complex is this sports facility"
                "located where 1990 FIFA World Cup Final between West"
                "Germany and Argentina took place?")
    content = f"Answer the question: {question}"

    user_msg = BaseMessage.make_user_message(role_name=role_name,
                                             content=content)
    react_agent.step(user_msg)


if __name__ == '__main__':
    main()
