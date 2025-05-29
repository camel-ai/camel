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
from camel.configs import ModelScopeConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.MODELSCOPE,
    model_type=ModelType.MODELSCOPE_QWEN_2_5_32B_INSTRUCT,
    model_config_dict=ModelScopeConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=[
        *MathToolkit().get_tools(),
    ],
)
# Let agent step the message
response = agent.step(
    "Assume now is 2024 in the Gregorian calendar, University of Oxford was set up in 1096, estimate the current age of University of Oxford"  # noqa: E501
)

# Check tool calling
print(response)
print(response.info['tool_calls'])
print(response.msgs[0].content)


'''
==============================================================================
msgs=[BaseMessage(role_name='Assistant', role_type=<RoleType.ASSISTANT: 'assistant'>, meta_dict={}, content='The University of Oxford is approximately 928 years old in the year 2024.', video_bytes=None, image_list=None, image_detail='auto', video_detail='low', parsed=None)] terminated=False info={'id': 'chatcmpl-6eeb61bf-1003-9fe3-962e-88ffe5d1704e', 'usage': {'completion_tokens': 22, 'prompt_tokens': 717, 'total_tokens': 739, 'completion_tokens_details': None, 'prompt_tokens_details': None}, 'termination_reasons': ['stop'], 'num_tokens': 80, 'tool_calls': [ToolCallingRecord(tool_name='sub', args={'a': 2024, 'b': 1096}, result=928, tool_call_id='call_05f85b0fdd9241be912883')], 'external_tool_call_requests': None}
[ToolCallingRecord(tool_name='sub', args={'a': 2024, 'b': 1096}, result=928, tool_call_id='call_05f85b0fdd9241be912883')]
The University of Oxford is approximately 928 years old in the year 2024.
==============================================================================
'''  # noqa: E501

model = ModelFactory.create(
    model_platform=ModelPlatformType.MODELSCOPE,
    model_type=ModelType.MODELSCOPE_QWEN_3_235B_A22B,
    model_config_dict=ModelScopeConfig(
        temperature=0.2,
        stream=True,
        extra_body={"enable_thinking": True, "thinking_budget": 10000},
    ).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
)

user_msg = """Say hi to CAMEL AI, one open-source community
    dedicated to the study of autonomous and communicative agents."""

# Let agent step the message
response = agent.step(user_msg)

# Get response information
print(response.msgs[0].content)


'''
==============================================================================
<think>
Okay, the user wants me to say hi to CAMEL AI, an open-source community focused on autonomous and communicative agents. Let me start by understanding what exactly they're asking for.

First, I need to acknowledge the greeting request. The user might be part of this community or just introducing it to me. Either way, my response should be friendly and welcoming. Since CAMEL AI is about autonomous and communicative agents, I should mention their dedication to studying these areas. Maybe highlight collaboration and innovation since those are common in open-source communities.

I should make sure to keep the tone positive and encouraging. Perhaps invite them to share more about their work or how others can get involved. That adds value beyond a simple greeting. Also, using emojis could make the message feel warmer and more approachable.

Wait, do I know specific projects or achievements of CAMEL AI? The user didn't provide details, so I should keep it general but still relevant. Focus on the key aspects: open-source, autonomous agents, communication, community-driven. Avoid any technical jargon that might not be accurate without more info.

Double-check if there's a standard way to greet such communities. Probably a straightforward welcome with enthusiasm. Make sure to offer assistance or ask if they need anything specific related to their work. That shows willingness to help further.

Alright, structure the response: Greeting, acknowledgment of their mission, appreciation for their work, invitation to collaborate or share more, closing with positive emoji. Keep it concise but comprehensive enough.
</think>
Hello CAMEL AI! 🌟 It’s exciting to see an open-source community dedicated to advancing autonomous and communicative agents—pushing the boundaries of AI collaboration, adaptability, and real-world problem-solving. Whether you’re exploring multi-agent systems, LLMs, or decentralized intelligence, your work is paving the way for transformative innovations. 💡 How can we contribute or dive deeper into your projects? Let’s build the future together! 🚀  

*(P.S. If you’re looking for resources, partnerships, or feedback, feel free to share!)*
==============================================================================
'''  # noqa: E501, RUF001
