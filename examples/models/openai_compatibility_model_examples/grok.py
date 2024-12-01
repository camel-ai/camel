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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Take calling grok-beta model as an example
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="grok-beta",
    api_key="xai-...",
    url="https://api.x.ai/v1",
    model_config_dict={"max_tokens": 2000},
)

assistant_sys_msg = (
    "You are Grok, a chatbot inspired by the Hitchhikers Guide to the Galaxy."
)

agent = ChatAgent(assistant_sys_msg, model=model)

user_msg = """What is the meaning of life, the universe, and everything?"""

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
Ah, the ultimate question! According to the Hitchhiker's Guide to the Galaxy, 
the answer to the meaning of life, the universe, and everything is **42**. 
However, the trick lies in figuring out the actual question to which 42 is the 
answer. Isn't that just like life, full of mysteries and unanswered questions? 
Keep pondering, for the journey of discovery is as important as the answer 
itself!
===============================================================================
"""
