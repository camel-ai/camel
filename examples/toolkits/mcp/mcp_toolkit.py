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
import sys
from pathlib import Path

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import McpToolkit
from camel.types import ModelPlatformType, ModelType


async def main(server_transport: str = "stdio"):
    if server_transport == "stdio":
        mcp_toolkit = McpToolkit(
            command_or_url=sys.executable,
            args=[str(Path(__file__).parent / "mcp_server.py")],
        )
    else:
        # SSE mode, Must run the server first
        mcp_toolkit = McpToolkit("http://127.0.0.1:8000/sse")

    async with mcp_toolkit.connection() as toolkit:
        tools = toolkit.get_tools()

        # Define system message
        sys_msg = "You are a helpful assistant"
        model_config_dict = ChatGPTConfig(
            temperature=0.0,
        ).as_dict()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        # Set agent
        camel_agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=tools,
        )
        camel_agent.reset()

        # Define a user message
        usr_msg = "How is the weather in Chicago today?"

        # Get response information
        response = await camel_agent.astep(usr_msg)
        print(str(response.info['tool_calls'])[:1000])
        """
        ==========================================================================
        [ToolCallingRecord(tool_name='get_forecast', args={'latitude': 
        41.8781, 'longitude': -87.6298}, result='\nThis Afternoon:\n
        Temperature: 57°F\nWind: 15 mph WSW\nForecast: Sunny. High near 57, 
        with temperatures falling to around 55 in the afternoon. West 
        southwest wind around 15 mph, with gusts as high as 25 mph.\n\n---\n\n
        Tonight:\nTemperature: 39°F\nWind: 5 to 15 mph WSW\nForecast: Mostly 
        clear, with a low around 39. West southwest wind 5 to 15 mph, with 
        gusts as high as 25 mph.\n\n---\n\nMonday:\nTemperature: 64°F\nWind: 5 
        to 15 mph SW\nForecast: Sunny. High near 64, with temperatures falling 
        to around 62 in the afternoon. Southwest wind 5 to 15 mph, with gusts 
        as high as 25 mph.\n\n---\n\nMonday Night:\nTemperature: 43°F\nWind: 
        15 mph SW\nForecast: Mostly clear, with a low around 43. Southwest 
        wind around 15 mph, with gusts as high as 25 mph.\n\n---\n\nTuesday:\n
        Temperature: 44°F\nWind: 15 mph NNW\nForecast: Mostly sunny, with a 
        high near 44. North northwest wind around 15 mph.\n', t
        """

        usr_msg = "Please get the latest 3 weather alerts for California."

        # Get response information
        response = await camel_agent.astep(usr_msg)
        print(str(response.info['tool_calls'])[:1000])
        """
        ==========================================================================
        [ToolCallingRecord(tool_name='get_alerts', args={'state': 'CA'}, result
        ='\nEvent: Wind Advisory\nArea: Central Siskiyou County\nSeverity: 
        Moderate\nDescription: * WHAT...South winds 20 to 30 mph with gusts up 
        to 50 mph expected.\n\n* WHERE...Portions of central Siskiyou County. 
        This includes\nInterstate 5 from Weed to Grenada and portions of 
        Highway 97.\n\n* WHEN...Until 5 PM PDT this afternoon.\n\n* IMPACTS...
        Gusty winds will blow around unsecured objects. Tree\nlimbs could be 
        blown down and a few power outages may result.\nInstructions: Winds 
        this strong can make driving difficult, especially for high\nprofile 
        vehicles. Use extra caution.\n\nSecure outdoor objects.\n', 
        tool_call_id='call_JRDYuTjOjYrymXeFiWxcHZ5d')]
        """


if __name__ == "__main__":
    asyncio.run(main())
