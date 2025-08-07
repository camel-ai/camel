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
from camel.models import ModelFactory
from camel.toolkits import ZapierToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = """You are a helpful AI assistant that can use Zapier AI tools to 
perform various tasks. When using tools, first list the available tools using 
list_actions, then use the appropriate tool based on the task. Always provide 
clear explanations of what you're doing."""

# Set model config
tools = ZapierToolkit().get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# First, list available tools
usr_msg = "First, list all available Zapier tools."
response = camel_agent.step(usr_msg)
print("Available Tools:")
print(response.msg.content)
print("\n" + "=" * 80 + "\n")

# Now, use the translation tool
usr_msg = """Now that we can see the translation tool is available, please 
use it to translate 'hello camel' from en to zh. Use 
the tool ID from the list above and make sure to specify the language codes 
correctly in the instructions."""
response = camel_agent.step(usr_msg)
print("Translation Result:")
print(response.msg.content)

"""
===============================================================================
Here are the available Zapier tools:

1. **Gmail: Find Email**
   - **ID:** 0d82cfd3-2bd7-4e08-9f3d-692719e81a26
   - **Description:** This action allows you to find an email in Gmail based 
        on a search string.
   - **Parameters:**
     - `instructions`: Instructions for executing the action.
     - `Search_String`: The string to search for in the emails.

2. **Translate by Zapier: Translate Text**
   - **ID:** f7527450-d7c7-401f-a764-2f69f622e7f3
   - **Description:** This action translates text into a specified target 
        language.
   - **Parameters:**
     - `instructions`: Instructions for executing the action.
     - `Text`: The text to be translated.
     - `Target_Language`: The language to translate the text into.

If you need to perform a specific task using one of these tools, please let me 
know!

================================================================================

Translation Result:
The translation of "hello camel" from English to Chinese (zh) is:

**Translation:** 你好骆驼

- **Source Language:** English (en)
- **Target Language:** Chinese (zh)

If you need any further assistance or additional translations, feel free to 
ask!
===============================================================================
"""
