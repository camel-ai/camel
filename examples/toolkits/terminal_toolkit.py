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

import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType, ModelType

# Get current script directory
base_dir = os.path.dirname(os.path.abspath(__file__))
# Define workspace directory for the toolkit
workspace_dir = os.path.join(
    os.path.dirname(os.path.dirname(base_dir)), "workspace"
)

# Define system message
sys_msg = (
    "You are a System Administrator helping with log management tasks. "
    "You have access to terminal tools that can help you execute "
    "shell commands and search files. "
)

# Set model config
tools = TerminalToolkit(working_dir=workspace_dir).get_tools()

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

# Define a user message for creating logs directory
usr_msg = (
    f"Create a 'logs' directory in '{workspace_dir}' and list its contents"
)

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'session1', 'exec_dir': 
'/Users/enrei/Desktop/camel0302/camel/workspace', 'command': 'mkdir logs'}, 
result='', tool_call_id='call_ekWtDhrwxOg20lz55pqLEKvm'), ToolCallingRecord
(tool_name='shell_exec', args={'id': 'session2', 'exec_dir': '/Users/enrei/
Desktop/camel0302/camel/workspace/logs', 'command': 'ls -la'}, result='total 
0\ndrwxr-xr-x  2 enrei  staff   64 Mar 30 04:29 .\ndrwxr-xr-x  4 enrei  staff  
128 Mar 30 04:29 ..\n', tool_call_id='call_FNdkLkvUahtEZUf7YZiJrjfo')]
===============================================================================
"""

# Define a user message for creating log files
usr_msg = (
    f"Create 'app.log' in the logs directory at "
    f"'{os.path.join(workspace_dir, 'logs')}' with content: INFO: Application "
    f"started successfully at 2024-03-10 and show the file content"
)

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'create_log_file', 
'exec_dir': '/Users/enrei/Desktop/camel0302/camel/workspace/logs', 'command': 
"echo 'INFO: Application started successfully at 2024-03-10' > app.log"}, 
result='', tool_call_id='call_bctQQYnWgAuPp1ga7a7xM6bo'), ToolCallingRecord
(tool_name='shell_exec', args={'id': 'show_log_file_content', 'exec_dir': '/
Users/enrei/Desktop/camel0302/camel/workspace/logs', 'command': 'cat app.
log'}, result='INFO: Application started successfully at 2024-03-10\n', 
tool_call_id='call_wPYJBG3eYrUsjFJYIYYynxuz')]
===============================================================================
"""

# Define a user message for searching in logs
usr_msg = (
    f"Search for 'INFO' keyword in the log file at "
    f"'{os.path.join(workspace_dir, 'logs', 'app.log')}'"
)

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='file_find_in_content', args={'file': '/Users/
enrei/Desktop/camel0302/camel/workspace/logs/app.log', 'regex': 'INFO', 
'sudo': False}, result='INFO: Application started successfully at 2024-03-10',
 tool_call_id='call_PpeRUsldHyg5jSPLZxiGoVfq')]
===============================================================================
"""

# Define a user message for cleaning up logs
usr_msg = (
    f"Remove the 'logs' directory and all its contents in '{workspace_dir}'"
)

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'remove_logs', 
'exec_dir': '/Users/enrei/Desktop/camel0302/camel/workspace', 'command': 'rm 
-rf logs'}, result='', tool_call_id='call_A2kUkVIAhkD9flWmmpTlS9FA')]
===============================================================================
"""

# Define a user message for find the content of the log file
usr_msg = "Find all the files under path `examples/bots`"

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[ToolCallingRecord(tool_name='file_find_by_name', args={'path': 'examples/
bots', 'glob': '*'}, result='examples/bots\nexamples/bots/discord_bot.
py\nexamples/bots/discord_bot_installation_management.py\nexamples/bots/
slack_bot_use_msg_queue.py\nexamples/bots/discord_bot_use_msg_queue.
py\nexamples/bots/slack_bot.py', tool_call_id='call_LzRjSotNqKOWwU4yHcstlnG9')]
===============================================================================
"""
