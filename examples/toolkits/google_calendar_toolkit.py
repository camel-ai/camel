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

from camel.agents import ChatAgent
from camel.configs import BaseConfig
from camel.models import ModelFactory
from camel.toolkits import GoogleCalendarToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=BaseConfig().as_dict(),
)

calendar_toolkit = GoogleCalendarToolkit()
calendar_tool = calendar_toolkit.get_tools()

agent = ChatAgent(model=model, tools=calendar_tool)

response = agent.step("What events from 3/30/2025 to the 4/5/2025")
print(str(response.info['tool_calls'])[:1000])
'''
===============================================================================
[ToolCallingRecord(tool_name='get_events', args={'max_results': 10, 'time_min' 
:'2025-03-30T00:00:00Z'}, 
result=[{'Event ID': 'xxx_20250401T143000Z', 
'Summary': 'Weekly catchup', 
'Start Time': '2025-04-01T20:00:00+05:30', 
'Link': 'https://www.google.com/calendar/event?eid=xxx'}]
===============================================================================
'''
