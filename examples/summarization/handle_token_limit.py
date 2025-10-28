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


model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
    summarize_threshold=1,
    summary_window_ratio=0.02,
)
camel_agent.reset()

# Define a user message for creating logs directory
usr_msg = (
    f"Create a 'logs' directory in '{workspace_dir}' and list its contents"
)

# simulate a long conversation
for _i in range(20):
    response = camel_agent.step(usr_msg)
    print(camel_agent._summary_token_count)

# handle a large file
usr_msg = "../../uv.lock,read this file"

response = camel_agent.step(usr_msg)
