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

# To use OutlookCalendarToolkit make sure to set required
# environment variables:
# MICROSOFT_CLIENT_ID
# MICROSOFT_CLIENT_SECRET
# MICROSOFT_TENANT_ID (optional, defaults to "common")
# Also ensure your Azure app has Calendars.ReadWrite (delegated) permissions
# and http://localhost as a redirect URI.

import asyncio

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import OutlookCalendarToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Initialize the toolkit
toolkit = OutlookCalendarToolkit()
tools = toolkit.get_tools()

# Define system message
sys_msg = (
    "You are a helpful assistant that manages Outlook calendar events. "
    "Use the provided tools to help users with their calendar tasks."
)

# Create agent with calendar tools
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)


async def main():
    # Example: List upcoming events
    response = await agent.astep("List my calendar events for the next 7 days")
    print("List Events Response:")
    print(response.msgs[0].content)
    print("\nTool calls:")
    print(str(response.info['tool_calls'])[:1000])


if __name__ == "__main__":
    asyncio.run(main())

"""
===============================================================================
List Events Response:
Here are your calendar events for the next 7 days:

1. **Team Standup**
   - Start: 2024-12-12T09:00:00
   - End: 2024-12-12T09:30:00
   - Location: Conference Room A

2. **Project Review**
   - Start: 2024-12-13T14:00:00
   - End: 2024-12-13T15:00:00
   - Location: Virtual Meeting

Tool calls:
[ToolCallingRecord(tool_name='list_calendar_events', args={'filter_query':
"start/dateTime ge '2024-12-11T00:00:00' and start/dateTime le
'2024-12-18T23:59:59'", 'order_by': ['start/dateTime asc'], 'top': 20},
result={'success': True, 'events': [{'id': 'AAMkAG...', 'subject':
'Team Standup', 'start': {'dateTime': '2024-12-12T09:00:00', 'timeZone':
'UTC'}, ...}]})]
===============================================================================
"""
