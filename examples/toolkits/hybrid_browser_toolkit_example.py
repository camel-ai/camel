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
from camel.toolkits import HybridBrowserToolkit
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
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(
    logging.DEBUG
)

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

custom_tools = [
    "browser_open",
    "browser_click",
    "browser_type",
    "browser_enter",
]

web_toolkit_custom = HybridBrowserToolkit(
    headless=False,
    enabled_tools=custom_tools,
    browser_log_to_file=True,
    stealth=True,
    viewport_limit=True,
    connect_over_cdp=True,
    cdp_no_page=True,
    cdp_url="http://localhost:9222/"
)
print(f"Custom tools: {web_toolkit_custom.enabled_tools}")
agent = ChatAgent(
    model=model_backend,
    tools=[*web_toolkit_custom.get_tools()],
    toolkits_to_register_agent=[web_toolkit_custom],
    max_iteration=10,
)

TASK_PROMPT = r"""
open browser然后帮我填写表单
用车类型为个人用车, 
用车场景为学生用车, 
下单人为18668079187，
派单类型为人工派单，
商业产品类型为多日包车，
订单类型为包车单，
服务等级为梅赛德斯-奔驰 S级，
用车时间为2025-09-10 14:54 （type输入）

上面这些信息如果没有radio就直接用browser_type输入，输入的对象为combobox或textbox, 只有radio用click，其他直接用browser_type输入.输入完成后用enter

"""


async def main() -> None:
        response = await agent.astep(TASK_PROMPT)
        await web_toolkit_custom.disconnect_websocket()

        print(response)

if __name__ == "__main__":
    asyncio.run(main())
