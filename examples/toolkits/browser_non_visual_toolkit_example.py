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
from camel.models import ModelFactory
from camel.toolkits import BrowserNonVisualToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('browser_dom_debug.log'),  # File output
    ],
)

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)

USER_DATA_DIR = r"User_Data"

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)


web_toolkit = BrowserNonVisualToolkit(
    headless=False,
    user_data_dir=USER_DATA_DIR,
)

agent = ChatAgent(
    system_message="""
    """,
    model=model_backend,
    tools=[*web_toolkit.get_tools()],
)


TASK_PROMPT = """Find the cheapest keyboard in Amazon, 
open the product page and add it to cart."""

response = agent.step(TASK_PROMPT)

print("Task:", TASK_PROMPT)
print(f"Using user data directory: {USER_DATA_DIR}\n")
print("Response from agent:")
print(response.msgs[0].content if response.msgs else "<no response>")
