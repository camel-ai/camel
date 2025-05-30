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
import os
from pathlib import Path

from camel.agents import MCPAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType


async def main():
    config_path = Path(__file__).parent / "mcp_servers_config.json"

    model = ModelFactory.create(
        url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        model_type="nvidia/llama-3.1-nemotron-70b-instruct:free",
    )

    mcp_agent = MCPAgent(
        config_path=str(config_path),
        model=model,
        function_calling_available=False,
    )
    await mcp_agent.connect()
    mcp_agent.add_mcp_tools()

    user_msg = (
        "I have 5 boxes, each of them containing 50 apples, "
        "how many apples in total. To solve this, use the calculator "
        "tools. Your response must include a JSON block formatted exactly "
        "like this:\n"
        "```json\n"
        "{\n"
        '  "server_idx": 0,\n'
        '  "tool_name": "multiply",\n'
        '  "tool_args": {"a": 5, "b": 50}\n'
        "}\n"
        "```"
    )
    response = await mcp_agent.run(user_msg)

    print(response.msgs[0].content)
    """
    The total number of apples is **250**.
    """

    # Disconnect from all MCP servers and clean up resources.
    await mcp_agent.close()


if __name__ == "__main__":
    asyncio.run(main())
