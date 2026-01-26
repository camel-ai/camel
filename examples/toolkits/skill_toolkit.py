# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import SkillToolkit
from camel.types import ModelPlatformType, ModelType

sys_msg = "You are a helpful assistant."

model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_MAX,
)

skill_toolkit = SkillToolkit()
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=[*skill_toolkit.get_tools()],
)

response = agent.step("List available skills.")
print(response.msgs[0].content)

"""
==============================================================================
Sure. I can list the available skills and load the most relevant one when
needed. Let me know the task you'd like to accomplish.
==============================================================================
"""
