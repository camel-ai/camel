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
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="What is 2+2?",
)

response = agent.step(user_msg)

print(f"User: {user_msg.content}")
print(f"Assistant: {response.msg.content}")

# Extract token usage from response
if response.info and 'usage' in response.info:
    usage = response.info['usage']
    print("\nToken Usage:")
    print(f"  Prompt tokens: {usage.get('prompt_tokens', 0)}")
    print(f"  Completion tokens: {usage.get('completion_tokens', 0)}")
    print(f"  Total tokens: {usage.get('total_tokens', 0)}")

'''
===============================================================================
User: What is 2+2?
Assistant: 2 + 2 equals 4.

Token Usage:
  Prompt tokens: 24
  Completion tokens: 8
  Total tokens: 32
===============================================================================
'''
