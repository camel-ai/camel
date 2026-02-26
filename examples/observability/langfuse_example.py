#!/usr/bin/env python3
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

"""
Preparation before running:
1. Set environment variables:
   - LANGFUSE_ENABLED="true"           # Enable tracing
   - LANGFUSE_PUBLIC_KEY="pk-lf-..."   # Optional
   - LANGFUSE_SECRET_KEY="sk-lf-..."   # Optional

Note:
- Tracing will only be enabled if LANGFUSE_ENABLED=true is set
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import get_langfuse_status

math_toolkit = [*MathToolkit().get_tools()]

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Define system message
sys_msg = "You are a helpful AI assistant, skilled at answering questions."

# Create agent
camel_agent = ChatAgent(
    system_message=sys_msg, model=model, tools=math_toolkit
)

# User message
user_msg = "Calculate the square root after adding 222991 and 1111"

print(get_langfuse_status())

response = camel_agent.step(user_msg)
print(response.msgs[0].content)

"""
2026-02-26 10:51:58,880 - root - WARNING - Unknown model 'ZhipuAI/GLM-4.7-Flash': context window size not defined. Defaulting to 999_999_999.
{'configured': True, 'has_public_key': True, 'has_secret_key': True, 'env_enabled': True, 'host': 'https://cloud.langfuse.com', 'debug': False, 'current_session_id': None, 'langfuse_client_available': True}
I can help you with the addition part of your request. First, let me add 222991 and 1111:

222991 + 1111 = **224102**

However, I don't have access to a square root function with the available tools. The square root of 224102 is approximately **473.47** (rounded to 2 decimal places).

So the complete calculation would be:
1. Add 222991 and 1111 = 224102
2. Square root of 224102 ≈ 473.47

"""