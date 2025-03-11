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
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main(server_transport: str = "stdio"):
    if server_transport == "stdio":
        mcp_toolkit = MCPToolkit(
            command_or_url=sys.executable,
            args=[str(Path(__file__).parent / "mcp_server.py")],
        )
    else:
        # SSE mode, Must run the server first
        mcp_toolkit = MCPToolkit("http://127.0.0.1:8000/sse")

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
        print(str(response.info['tool_calls']))
        """
        =======================================================================
        [ToolCallingRecord(tool_name='get_forecast', args={'latitude': 41.
        8781, 'longitude': -87.6298}, result='\nThis Afternoon:\nTemperature: 
        65°F\nWind: 15 mph SW\nForecast: Sunny, with a high near 65. Southwest 
        wind around 15 mph, with gusts as high as 25 mph.
        \n\n---\n\nTonight:\nTemperature: 45°F\nWind: 10 to 15 mph 
        SW\nForecast: Mostly clear. Low around 45, with temperatures rising to
         around 51 overnight. Southwest wind 10 to 15 mph, with gusts as high 
         as 30 mph.\n\n---\n\nTuesday:\nTemperature: 46°F\nWind: 10 to 20 mph 
         NW\nForecast: Mostly sunny. High near 46, with temperatures falling 
         to around 36 in the afternoon. Northwest wind 10 to 20 mph, with 
         gusts as high as 35 mph.\n\n---\n\nTuesday Night:\nTemperature: 36°
         F\nWind: 10 to 20 mph ENE\nForecast: Partly cloudy, with a low around 
         36. East northeast wind 10 to 20 mph.
         \n\n---\n\nWednesday:\nTemperature: 46°F\nWind: 5 to 15 mph 
         E\nForecast: Mostly sunny, with a high near 46. East wind 5 to 15 mph.
         \n', tool_call_id='call_DJjGYAzqlzb5ojirRAuKZmtk')]
        =======================================================================
        """

        usr_msg = "Please get the latest 3 weather alerts for California."

        # Get response information
        response = await camel_agent.astep(usr_msg)
        print(str(response.info['tool_calls']))
        """
        =======================================================================
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
        =======================================================================
        """


if __name__ == "__main__":
    asyncio.run(main())
