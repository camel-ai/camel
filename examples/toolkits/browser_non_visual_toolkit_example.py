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
import asyncio
import logging

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import BrowserNonVisualToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits.non_visual_browser_toolkit').setLevel(
    logging.DEBUG
)
USER_DATA_DIR = "User_Data"

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

web_toolkit = BrowserNonVisualToolkit(
    headless=False, user_data_dir=USER_DATA_DIR
)

agent = ChatAgent(
    model=model_backend,
    tools=[*web_toolkit.get_tools()],
    max_iteration=10,
)

TASK_PROMPT = """Play this game: 
https://www.nytimes.com/games/wordle/index.html
You need to enter meaningful five-letter words, such as "Apple".
Before completing the task, do not do anything outside of using the call tool.
If the game tells you that something is wrong, you must resolve it yourself.
Also, you must attempt all six tries.

If the registration window can be closed, please close it.
"""


async def main() -> None:
    response = await agent.astep(TASK_PROMPT)
    print("Task:", TASK_PROMPT)
    print(f"Using user data directory: {USER_DATA_DIR}\n")
    print("Response from agent:")
    print(response.msgs[0].content if response.msgs else "<no response>")

    try:
        await web_toolkit.close_browser()
    except Exception as err:
        logging.warning("Failed to close browser session explicitly: %s", err)


if __name__ == "__main__":
    asyncio.run(main())
