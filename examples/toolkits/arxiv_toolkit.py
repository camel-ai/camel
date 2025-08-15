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
from camel.toolkits import ArxivToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = "You are a helpful assistant"

# Set model config
tools = ArxivToolkit().get_tools()

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

# Define a user message
usr_msg = "Search paper 'attention is all you need' for me"

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
'''
===============================================================================
[ToolCallingRecord(func_name='search_papers', args={'query': 'attention is 
all you need'}, result=[{'title': "Attention Is All You Need But You Don't 
Need All Of It For Inference of Large Language Models", 'published_date': 
'2024-07-22', 'authors': ['Georgy Tyukin', 'Gbetondji J-S Dovonon', 'Jean 
Kaddour', 'Pasquale Minervini'], 'entry_id': 'http://arxiv.org/abs/2407.
15516v1', 'summary': 'The inference demand for LLMs has skyrocketed in recent 
months, and serving\nmodels with low latencies remains challenging due to the 
quadratic input length\ncomplexity of the attention layers. In this work, we 
investigate the effect of\ndropping MLP and attention layers at inference time 
on the performance of\nLlama-v2 models. We find that dropping dreeper 
attention layers only marginally\ndecreases performance but leads to the best 
speedups alongside dropping entire\nlayers. For example, removing 33\\% of 
attention layers in a 13B Llama2 model\nresults in a 1.8\\% drop in average 
performance ove...
===============================================================================
'''


# Define a user message
usr_msg = """Download paper "attention is all you need" for me to my 
    local path '/Users/enrei/Desktop/camel0826/camel/examples/tool_call'"""

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
'''
===============================================================================
[ToolCallingRecord(func_name='download_papers', args={'query': 'attention 
is all you need', 'output_dir': '/Users/enrei/Desktop/camel0826/camel/examples/
tool_call', 'paper_ids': ['2407.15516v1', '2107.08000v1', '2306.01926v1', 
'2112.05993v1', '1912.11959v2']}, result='papers downloaded successfully')]
===============================================================================
'''
