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
tools = TerminalToolkit(working_directory=workspace_dir).get_tools()

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

# Define a user message for testing resource cleanup via __del__ method
print("\n\n================ Testing Resource Cleanup ================")
usr_msg = (
    "Start a long-running process that sleeps for 300 seconds in the "
    "background, then show me the list of running processes"
)


# Get response information for starting the process
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'session1', 'exec_dir': 
'/tmp', 'command': 'sleep 300 & echo $!'}, result='Operation restriction: 
Execution path /tmp must be within working directory /home/jjyaoao/openSource/
camel/workspace', tool_call_id='call_G7TcVUJs195Er6yocORHysXP'), 
ToolCallingRecord(tool_name='shell_exec', args={'id': 'session1', 'exec_dir': 
'/home/jjyaoao/openSource/camel/workspace', 'command': 'sleep 300 & echo $!'}, 
result='10804\n', tool_call_id='call_mncQosy3b4cuc1j5MGiltohH'), 
ToolCallingRecord(tool_name='shell_exec', args={'id': 'session2', 'exec_dir': 
'/home/jjyaoao/openSource/camel/workspace', 'command': 'ps aux'}, 
result='USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME 
COMMAND\nroot           1  0.0  0.2 170104 12368 ?        Ss   10:06   0:00 
/sbin/init\nroot           2  0.0  0.0   2776  1928 ?        Sl   10:06   0:00 
/init\nroot           8  0.0  0.0   2776     4 ?        Sl   10:06   0:00 
plan9 --control-socket 7 --log-level=debug --log-file=/dev/null ...',
tool_call_id='call_UvxQrsb1GpfDHTQQc6rLoQ3P')]
===============================================================================
"""
# Define a user message to check if the process was terminated by __del__
usr_msg = "Check if there are any sleep processes running on the system"

# Get response information for checking the processes
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'check_sleep_processes',
'exec_dir': '/', 'command': 'ps aux | grep sleep'}, result='Operation 
restriction: Execution path / must be within working directory 
/home/jjyaoao/openSource/camel/workspace', tool_call_id=
'call_gbhmZ3mwpB07uPtVF3FxZaHu'), ToolCallingRecord(tool_name='shell_exec',
args={'id': 'check_sleep_processes', 'exec_dir': 
'/home/jjyaoao/openSource/camel/workspace', 'command': 'ps aux | grep sleep'}, 
result='root       11385  0.0  0.0   2620   532 pts/4    S+   11:16   0:00 
/bin/sh -c ps aux | grep sleep\nroot       11387  0.0  0.0   8172   656 pts/4  
S+   11:16   0:00 grep sleep\n', tool_call_id='call_gSZqRaqNAtYjUXOfvVuaObw2')]
===============================================================================
"""

usr_msg = "help me use uv pip install pptx, and create a ppt, and show me the"
" output of the terminal"

# Get response information for checking the processes
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls']))

usr_msg = (
    "Use the terminal tool to create a Python file named 'python_file', "
    "but first, you need to request user help using call_user_for_help. "
    "The user will assist you with some configurations. "
    "Then, create the Python file, and finally list the contents of the "
    "current folder."
)

# Get response information for checking the processes
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls']))
"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': '1', 'command': 'pip 
install python-pptx'}, result='\nStderr Output:\n/Users/enrei/Desktop/
camel0605/camel/.venv/bin/python3: No module named pip\n', 
tool_call_id='call_ogvH8cKGGBMlulMV6IOCyN4q')]

============================================================
🤖 CAMEL Agent needs human help! Session: terminal_session_1
📂 Working directory: /Users/enrei/Desktop/camel0605/camel/workspace
============================================================
💡 Type commands or '/exit' to return control to agent.
============================================================

🧑‍💻 [terminal_session_1]> uv pip install python-pptx

Stderr Output:
Using Python 3.10.16 environment at: /Users/enrei/Desktop/camel0605/camel/.venv
Audited 1 package in 16ms


============================================================
✅ Human assistance completed! Commands: 1
🤖 Returning control to CAMEL agent...
============================================================

[ToolCallingRecord(tool_name='ask_user_for_help', args={'id': 
'terminal_session_1'}, result="Human assistance completed successfully for 
session 'terminal_session_1'. Total commands executed: 1. Working directory: /
Users/enrei/Desktop/camel0605/camel/workspace", 
tool_call_id='call_eYtpU38YncR6PnfdlBqouSoV'), ToolCallingRecord
(tool_name='file_find_by_name', args={'path': '/Users/enrei/Desktop/camel0605/
camel/workspace', 'glob': 'python_file'}, result='', 
tool_call_id='call_pyuYHoNvpPvXFbMjfo9DMUNe'), ToolCallingRecord
(tool_name='file_find_by_name', args={'path': '/Users/enrei/Desktop/camel0605/
camel/workspace', 'glob': '*'}, result='/Users/enrei/Desktop/camel0605/camel/
workspace\n/Users/enrei/Desktop/camel0605/camel/workspace/.venv\n/Users/enrei/
Desktop/camel0605/camel/workspace/.venv/bin\n/Users/enrei/Desktop/camel0605/
camel/workspace/.venv/bin/python3\n/Users/enrei/Desktop/camel0605/camel/
workspace/.venv/bin/python\n/Users/enrei/Desktop/camel0605/camel/workspace/.
venv/bin/python3.12\n/Users/enrei/Desktop/camel0605/camel/workspace/.venv/
include\n/Users/enrei/Desktop/camel0605/camel/workspace/.venv/include/python3.
12\n/Users/enrei/Desktop/camel0605/camel/workspace/.venv/pyvenv.cfg\n/Users/
enrei/Desktop/camel0605/camel/workspace/.venv/lib\n/Users/enrei/Desktop/
camel0605/camel/workspace/.venv/lib/python3.12\n/Users/enrei/Desktop/camel0605/
camel/workspace/.venv/lib/python3.12/site-packages', 
tool_call_id='call_WwB219FGm4tAssjFA9UsIrRT'), ToolCallingRecord
(tool_name='shell_exec', args={'id': 'terminal_session_1', 'command': 'touch
python_file.py'}, result='', tool_call_id='call_OBhkDr5i2mzBRpty0JiSF8Dj'),
ToolCallingRecord(tool_name='shell_exec', args={'id': 'terminal_session_1',
'command': 'ls -l'}, result='total 0\n-rw-r--r--  1 enrei  staff  0 Jun 27 
17:26 python_file.py\n', tool_call_id='call_fllEujXWutTJmqpSWpHOOnIU')]
(.venv) enrei@192 camel % 
===============================================================================
"""

# ------Docker backend------
tools = TerminalToolkit(
    use_docker_backend=True,
    # use your own container name
    docker_container_name="example_container",
    safe_mode=False,
).get_tools()

sys_msg = "You are a helpful assistant."

agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)
agent.reset()

usr_msg = "list all files in the current directory"
response = agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

"""
===============================================================================
[ToolCallingRecord(tool_name='shell_exec', args={'id': 'sess1', 'command': 
'ls -la', 'block': True}, result='total 12\ndrwxr-xr-x 3 root root 4096 Sep 
23 16:48 .\ndrwxr-xr-x 1 root root 4096 Sep 23 16:47 ..\ndrwxr-xr-x 2 root 
root 4096 Sep 23 16:49 logs', tool_call_id='call_YRYlz8KozpxXE2uGkcHIUnZU', 
images=None)]
===============================================================================
"""
