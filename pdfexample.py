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
# ruff: noqa: E501
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FileWriteToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0},
)

# Define system message for the agent
sys_msg = "You are a helpful assistant that can create and modify files."

# Set up output directory
output_dir = "./file_write_outputs"
os.makedirs(output_dir, exist_ok=True)

# Initialize the FileWriteToolkit with the output directory
file_toolkit = FileWriteToolkit(output_dir=output_dir)

# Get the tools from the toolkit
tools_list = file_toolkit.get_tools()

# Initialize a ChatAgent with the tools
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools_list,
)


# Example 8: what is multiagent? please export them as pdf file
pdf_query = """please write a blog,which contain there paragraphs and each paragraph has a numbertalbe , please only export them as pdf file"""

camel_agent.reset()
response = camel_agent.step(pdf_query)
print(f"Example 8: {pdf_query}")
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])
print("\n")

'''
===============================================================================
Example 8: what is multiagent? please export them as pdf file
The information about multiagent systems has been successfully exported to a PDF file named "multiagent_overview.pdf". If you need any further assistance, feel free to ask!
Tool calls: [ToolCallingRecord(tool_name='write_to_file', args={'content': '### What is Multiagent?\n\nMultiagent systems (MAS) are systems composed of multiple interacting intelligent agents.
These agents can be software programs, robots, or any entities that can perceive their environment and act upon it. The key characteristics of multiagent systems include:\n\n
1. **Autonomy**: Each agent operates independently and makes its own decisions.\n2. **Social Ability**: Agents can communicate and interact with each other to achieve their goals.
\n3. **Reactivity**: Agents can respond to changes in their environment in real-time.\n4. **Proactiveness**: Agents can take initiative and act in anticipation of future events.\n\n
### Applications of Multiagent Systems\n\nMultiagent systems are used in various fields, including:\n- **Robotics**: Coordinating multiple robots to perform tasks.\n- **Distributed Control**:
# Managing resources in smart grids or traffic systems.\n- **Game Theory**: Analyzing strategies in competitive environments.\n- **Simulation**: Modeling complex systems in economics, biology,
# and social sciences.\n\n### Conclusion\n\nMultiagent systems provide a framework for understanding and designing systems where multiple agents interact, leading to complex behaviors and solutions to problems that are difficult for a single agent to solve alone.',
#  'filename': 'multiagent_overview.pdf', 'encoding': None, 'use_latex': False}, result='Content successfully written to file: /Users/yifengwang/project/camel/file_write_outputs/multiagent_overview.pdf', tool_call_id='call_btYqjycX4aUfBNJUy8bpnHSV')]
===============================================================================
'''
