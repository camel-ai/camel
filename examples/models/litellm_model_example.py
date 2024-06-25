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
from camel.agents import ChatAgent
from camel.configs import LiteLLMConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

model = ModelFactory.create(
    model_platform=ModelPlatformType.LITELLM,
    model_type="gpt-4o",
    model_config_dict=LiteLLMConfig(temperature=0.2).__dict__,
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model, token_limit=500)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""CAMEL AI integrate LiteLLM into their multi agent framework,
    write a short post to announce it!""",
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
🚀 Exciting News from CAMEL AI! 🚀

We are thrilled to announce the integration of LiteLLM into our multi-agent 
framework! 🎉

At CAMEL AI, we are committed to pushing the boundaries of artificial 
intelligence and enhancing the capabilities of our multi-agent systems. With 
LiteLLM, we are taking a significant leap forward in delivering more 
efficient, scalable, and intelligent solutions.

LiteLLM, known for its lightweight and high-performance language models, will 
empower our agents to process and understand natural language with 
unprecedented speed and accuracy. This integration will not only boost the 
performance of our AI agents but also open up new possibilities for innovative 
applications across various industries.

Stay tuned for more updates as we continue to innovate and bring you the best 
in AI technology. Thank you for your continued support!

#CAMELAI #LiteLLM #AI #Innovation #MultiAgentSystems #TechNews
===============================================================================
'''
