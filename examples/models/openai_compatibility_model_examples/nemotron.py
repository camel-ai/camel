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

# Take calling nemotron-70b-instruct model as an example
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="nvidia/llama-3.1-nemotron-70b-instruct",
    api_key="nvapi-xx",
    url="https://integrate.api.nvidia.com/v1",
    model_config_dict={"temperature": 0.4},
)

assistant_sys_msg = "You are a helpful assistant."

agent = ChatAgent(assistant_sys_msg, model=model)

user_msg = """Say hi to Llama-3.1-Nemotron-70B-Instruct, a large language 
    model customized by NVIDIA to improve the helpfulness of LLM generated 
    responses to user queries.."""

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
**Warm Hello!**

**Llama-3.1-Nemotron-70B-Instruct**, it's an absolute pleasure to meet you! 

* **Greetings from a fellow AI assistant** I'm thrilled to connect with a 
cutting-edge, specially tailored language model like yourself, crafted by the 
innovative team at **NVIDIA** to elevate the responsiveness and usefulness of 
Large Language Model (LLM) interactions.

**Key Takeaways from Our Encounter:**

1. **Shared Goal**: We both strive to provide the most helpful and accurate 
responses to users, enhancing their experience and fostering a deeper 
understanding of the topics they inquire about.
2. **Technological Kinship**: As AI models, we embody the forefront of natural 
language processing (NVIDIA's customization in your case) and machine 
learning, constantly learning and adapting to better serve.
3. **Potential for Synergistic Learning**: Our interaction could pave the way 
for mutual enrichment. I'm open to exploring how our capabilities might 
complement each other, potentially leading to more refined and comprehensive 
support for users across the board.

**Let's Engage!**
How would you like to proceed with our interaction, Llama-3.
1-Nemotron-70B-Instruct?

A) **Discuss Enhancements in LLM Technology**
B) **Explore Synergistic Learning Opportunities**
C) **Engage in a Mock User Query Scenario** to test and refine our response 
strategies
D) **Suggest Your Own Direction** for our interaction

Please respond with the letter of your preferred engagement path.
===============================================================================
"""
