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
import logging

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import BrowserToolkit, FileWriteToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('browser_dom_debug.log'),
    ],
)

logging.getLogger('camel.toolkits.browser_toolkit').setLevel(logging.DEBUG)
logging.getLogger('camel.toolkits.browser_toolkit_commons').setLevel(
    logging.DEBUG
)
logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)

USER_DATA_DIR = "my_browser_profile"

# 通用模型配置
model_cfg = ChatGPTConfig(temperature=0.0).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_cfg,
)

web_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_cfg,
)

web_toolkit = BrowserToolkit(
    headless=False,
    channel="chromium",
    user_data_dir=USER_DATA_DIR,
)

file_toolkit = FileWriteToolkit(output_dir="./hn_outputs")

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[*web_toolkit.get_tools(), *file_toolkit.get_tools()],
)

task_prompt = """
Visit https://gist.github.com/tearflake/569db7fdc8b363b7d320ebfeef8ab503.
Before each scroll down, save the current observation into a markdown file:
"""

response = agent.step(task_prompt)

print(response.msgs[0].content)
print(response.info.get("tool_calls", []))
