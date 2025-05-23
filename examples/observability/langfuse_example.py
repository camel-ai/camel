#!/usr/bin/env python3
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

"""
Preparation before running:
1. Set environment variables:
   - LANGFUSE_ENABLED="true"           # Enable tracing
   - LANGFUSE_PUBLIC_KEY="pk-lf-..."   # Optional
   - LANGFUSE_SECRET_KEY="sk-lf-..."   # Optional

Note:
- Tracing will only be enabled if LANGFUSE_ENABLED=true is set
- If Langfuse keys are not set, the code will still run normally, just without tracing
"""

import os
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Enable Langfuse tracing (optional)
os.environ["LANGFUSE_ENABLED"] = "true"

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1_MINI,
)

from camel.utils import get_langfuse_status
status = get_langfuse_status()
print("Configuration successful:", status.get("configured"))

# Define system message
sys_msg = "You are a helpful AI assistant, skilled at answering questions."

# Create agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

# User message
user_msg = "Please introduce the CAMEL AI open-source community and explain its main features."

# Get response (if Langfuse is configured, it will automatically trace)
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
