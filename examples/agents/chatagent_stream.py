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
from camel.types import ModelPlatformType, ModelType

# Create a streaming model
streaming_model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={
        "stream": True,
        "stream_options": {"include_usage": True},
    },
)

agent = ChatAgent(
    system_message="You are a helpful assistant that provides detailed "
    "and informative responses.",
    model=streaming_model,
)

# Example user message
user_message = "Tell me about the benefits of renewable energy and how "
"it impacts the environment."

# Get streaming response
streaming_response = agent.step(user_message)

# Stream the response chunks
for chunk_response in streaming_response:
    # Each chunk_response is a ChatAgentResponse with incremental content
    chunk_content = chunk_response.msgs[0].content
    print(chunk_content, end="", flush=True)
