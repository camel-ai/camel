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
from camel.toolkits import NetworkXToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = "You are a helpful assistant for graph analysis"

# Set model config and initialize toolkit
tools = NetworkXToolkit(graph_type='digraph').get_tools()

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

# Example: Create a directed graph and perform some analysis
usr_msg = """Create a directed graph with the following edges:
- A -> B (weight: 2)
- B -> C (weight: 3)
- C -> A (weight: 1)
Then find the shortest path from A to C and calculate the graph density."""

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls']))

'''
===============================================================================
[ToolCallingRecord(tool_name='add_edge', args={'source': 'A', 'target': 'B'}, 
result=None, tool_call_id='call_iewKMXQd2GKwKWy7XJ5e5d8e'), ToolCallingRecord
(tool_name='add_edge', args={'source': 'A', 'target': 'B'}, result=None, 
tool_call_id='call_Xn8wq22oKeKekuPEqcSj5HuJ'), ToolCallingRecord
(tool_name='add_edge', args={'source': 'B', 'target': 'C'}, result=None, 
tool_call_id='call_bPeCvUBk1iQ6vv5060Zd7nbi'), ToolCallingRecord
(tool_name='add_edge', args={'source': 'C', 'target': 'A'}, result=None, 
tool_call_id='call_inCnY60iSBVghsrrHEDh7hNw'), ToolCallingRecord
(tool_name='get_shortest_path', args={'source': 'A', 'target': 'C', 'weight': 
'weight', 'method': 'dijkstra'}, result=['A', 'B', 'C'], 
tool_call_id='call_Gwy3Ca8RDQCZFuiy2h0Z6SSF'), ToolCallingRecord
(tool_name='get_edges', args={}, result=[('A', 'B'), ('B', 'C'), ('C', 'A')], 
tool_call_id='call_LU2xhb2W4h5a6LOx4U8gLuxa'), ToolCallingRecord
(tool_name='get_nodes', args={}, result=['A', 'B', 'C'], 
tool_call_id='call_WLuB1nBrhFeGj4FKrbwfnCrG')]
===============================================================================
'''
