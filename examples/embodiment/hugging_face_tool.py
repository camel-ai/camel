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
from typing import List

from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.agents.tool_agents.base import BaseToolAgent
from camel.generators import SystemMessageGenerator
from camel.types import RoleType


def main():
    # Create an embodied agent
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT),
    )
    tool_agents = [
        HuggingFaceToolAgent(
            'hugging_face_tool_agent',
            remote=True,
        )
    ]
    tool_agents: List[BaseToolAgent]
    embodied_agent = EmbodiedAgent(
        sys_msg,
        verbose=True,
        tool_agents=tool_agents,
    )

    user_msg = (
        "Draw all the Camelidae species, "
        "caption the image content, "
        "save the images by species name."
    )
    response = embodied_agent.step(user_msg)
    print(response.msg.content)


if __name__ == "__main__":
    main()
