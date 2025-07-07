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

from camel.agents import ChatAgent
from camel.toolkits import OrigeneToolkit


async def main():
    # Use async context manager for automatic connection management
    async with OrigeneToolkit() as origene_toolkit:
        user_msg = "what is the chemical structure of 1,2-dimethylbenzene?"
        agent = ChatAgent(
            "You are named origene assistant.",
            model="gpt-4o",
            tools=[*origene_toolkit.get_tools()],
        )
        response = agent.step(user_msg)
        print(response.msgs[0].content)
    # Toolkit is automatically disconnected when exiting the context


if __name__ == "__main__":
    asyncio.run(main())
