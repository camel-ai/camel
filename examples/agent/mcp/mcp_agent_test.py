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
from pathlib import Path

from camel.agents import MCPAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType


async def main():
    # TODO: modify the tool path in json file to your own path
    config_path = Path(__file__).parent / "mcp_servers_config.json"

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type="deepseek-r1:70b",
        model_config_dict={"max_tokens": 64000, "temperature": 0.5},
    )

    mcp_agent = MCPAgent(
        config_path=str(config_path), model=model, model_fc_available=False
    )
    await mcp_agent.connect()
    mcp_agent.add_mcp_tools()

    user_msg = (
        "I have 5 boxes, each of them contiaining 50 apples, "
        "how many apples in total."
    )
    response = await mcp_agent.run(user_msg)

    print(response.msgs[0].content)

    # Disconnect from all MCP servers and clean up resources.
    await mcp_agent.close()


if __name__ == "__main__":
    asyncio.run(main())
