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
from camel.toolkits import WebFetchToolkit
from camel.types import ModelPlatformType, ModelType

# Create the toolkit instance
web_fetch_toolkit = WebFetchToolkit()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# The toolkit extends RegisteredAgentToolkit, so pass it via
# toolkits_to_register_agent to let the agent register itself.
agent = ChatAgent(
    system_message="You are a helpful research assistant.",
    model=model,
    tools=web_fetch_toolkit.get_tools(),
    toolkits_to_register_agent=[web_fetch_toolkit],
)

response = agent.step(
    "Fetch https://httpbin.org/html and tell me what the page is about."
)
print(response.msgs[0].content)
