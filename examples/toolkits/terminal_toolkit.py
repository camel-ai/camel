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

# Define system message
sys_msg = (
    "You are a System Administrator helping with log management tasks. "
    "You have access to terminal tools that can help you execute "
    "shell commands and search files. "
)

# Set model config
tools = TerminalToolkit().get_tools()

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
usr_msg = f"Create a 'logs' directory in '{base_dir}'"

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'shell_session_1', 
'exec_dir': '/Users/enrei/Desktop/camel0302/camel/examples/toolkits', 
'command': 'mkdir logs'}, result="Command started in session 
'shell_session_1'. Initial output: ", 
tool_call_id='call_8xSHligODzyfPOMG81dGxNF2'), ToolCallingRecord
(tool_name='shell_wait', args={'id': 'shell_session_1', 'seconds': None}, 
result="Process completed in session 'shell_session_1'. Output: ", 
tool_call_id='call_3RZ8Pg2BlmfFoYWgmEVONdcE')]
===============================================================================
"""

# Define a user message for creating log files
usr_msg = f"""Create 'app.log' in the logs directory at '{os.path.join
(base_dir, 'logs')}' with content: 'INFO: Application started successfully at 
2024-03-10'"""

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'create_log_file', 
'exec_dir': '/Users/enrei/Desktop/camel0302/camel/examples/toolkits/logs', 
'command': "echo 'INFO: Application started successfully at 2024-03-10' > app.
log"}, result="Command started in session 'create_log_file'. Initial output: 
", tool_call_id='call_IK0vsGszfjw3hn5Jda1R8t4A'), ToolCallingRecord
(tool_name='shell_wait', args={'id': 'create_log_file', 'seconds': 5}, 
result="Process completed in session 'create_log_file'. Output: ", 
tool_call_id='call_ta8ksNQvrPcdvBgmAro692uJ')]
===============================================================================
"""

# Define a user message for searching in logs
usr_msg = (
    f"Search for 'INFO' keyword in the log file at "
    f"'{os.path.join(base_dir, 'logs', 'app.log')}'"
)

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='file_find_in_content', args={'file': '/Users/
enrei/Desktop/camel0302/camel/examples/toolkits/logs/app.log', 'regex': 
'INFO', 'sudo': False}, result='INFO: Application started successfully at 
2024-03-10', tool_call_id='call_mrrHw9rEwfLwJeSD1j0zooLd')]
===============================================================================
"""

# Define a user message for cleaning up logs
usr_msg = f"Remove the 'logs' directory and all its contents in '{base_dir}'"

# Get response information
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'remove_logs', 
'exec_dir': '/Users/enrei/Desktop/camel0302/camel/examples/toolkits', 
'command': 'rm -rf logs'}, result="Command started in session 'remove_logs'. 
Initial output: ", tool_call_id='call_DzBjpYowMmGbUrZ1C24TNuOy'), 
ToolCallingRecord(tool_name='shell_wait', args={'id': 'remove_logs', 
'seconds': None}, result="Process completed in session 'remove_logs'. Output: 
", tool_call_id='call_BchqhziSRi7t3av279Nt1u6E')]
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
py\nexamples/bots/slack_bot.py', tool_call_id='call_PBtQ7qzk2K9fnrtrTASbpeDb')]
===============================================================================
"""
