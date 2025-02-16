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
from camel.agents import EmbodiedAgent
from camel.generators import SystemMessageGenerator
from camel.types import RoleType


def main():
    # Create an embodied agent
    role_name = "Programmer"
    meta_dict = dict(role=role_name, task="Programming")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(role_name, RoleType.EMBODIMENT),
    )
    embodied_agent = EmbodiedAgent(
        sys_msg,
        verbose=True,
    )
    print(embodied_agent.system_message.content)

    user_msg = (
        "Write a bash script to install numpy, "
        "then write a python script to compute "
        "the dot product of [6.75,3] and [4,5] and print the result, "
        "then write a script to open a browser and search today's weather."
    )
    response = embodied_agent.step(user_msg)
    print(response.msg.content)


if __name__ == "__main__":
    main()
