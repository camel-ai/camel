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
import os
from typing import List

from camel.agents import EmbodiedAgent
from camel.agents.tool_agents.base import BaseToolAgent
from camel.agents.tool_agents.Google_tool_agent import GoogleToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import UserChatMessage
from camel.typing import RoleType


def main():
    role_name = "Searcher"
    meta_dict = dict(role=role_name, task="Answer questions")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=("f{role_name}'s Embodiment", RoleType.EMBODIMENT))

    # The tool to be used should be the Wikipedia API
    action_space = [GoogleToolAgent('google_tool_agent')]
    action_space: List[BaseToolAgent]

    embodiment_agent = EmbodiedAgent(
        sys_msg,
        verbose=True,
        action_space=action_space,
    )

    user_msg = UserChatMessage(
        role_name=role_name, content=
        ("Answer the question: Author David Chanoff has collaborated with a U.S. Navy admiral who served as the ambassador to the United Kingdom under which President?"
         ))
    output_message, _, _ = embodiment_agent.step(user_msg)
    print(output_message.content)


if __name__ == '__main__':
    os.environ['OPENAI_API_KEY'] = '<openai_api_key>'
    os.environ['SERPAPI_KEY'] = '<serpapi_key>'
    main()
