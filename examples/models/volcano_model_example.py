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

"""
Please set the below environment variable before running this example:
export VOLCANO_API_KEY="your_volcano_api_key"

Volcano Engine API supports various models including DeepSeek models.
This example uses the DeepSeek-R1 model.
"""

# Create a model using ModelFactory
model = ModelFactory.create(
    model_platform=ModelPlatformType.VOLCANO,
    model_type="deepseek-r1-250120",  # DeepSeek-R1 model
    model_config_dict={
        "temperature": 0.2,
        "max_tokens": 1024,
    },
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """How many r in strawberry."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
