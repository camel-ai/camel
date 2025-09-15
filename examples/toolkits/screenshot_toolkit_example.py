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
from pathlib import Path

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ScreenshotToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize the model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set up working directory
working_dir = Path("screenshot_example_workspace")
working_dir.mkdir(exist_ok=True)

# Create the ScreenshotToolkit
screenshot_toolkit = ScreenshotToolkit(
    working_directory=str(working_dir),
    timeout=30.0,
)

agent = ChatAgent(
    system_message=(
        "You are a helpful assistant that can take and analyze "
        "screenshots. When analyzing screenshots, describe what you see "
        "in detail, including any text, UI elements, applications, or "
        "content visible on the screen."
    ),
    model=model,
    tools=screenshot_toolkit.get_tools(),
    toolkits_to_register_agent=[screenshot_toolkit],
)

response = agent.step(
    "Take a screenshot called 'screen_analysis.png' and analyze what "
    "you see on the screen. Tell me about any applications, windows, "
    "or content visible."
)
print(f"Agent response: {response.msgs[0].content}")
