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
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import SearchToolkit
from camel.types import ModelPlatformType, ModelType

o3_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.O3_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)


# Set agent
camel_agent = ChatAgent(
    model=o3_model, tools=[SearchToolkit().search_duckduckgo]
)

# Set user message
user_msg = """Search what is deepseek r1, and do a comparison between deepseek 
r1 and openai o3 mini and let me know the advantages and disadvantages of 
openai o3 mini"""

# Get response information
response = camel_agent.step(user_msg)
print(str(response.info['tool_calls'])[:1000])
'''
===============================================================================
[ToolCallingRecord(func_name='search_duckduckgo', args={'query': 'what is 
deepseek r1, and do a comparison between deepseek r1 and openai o3 mini', 
'source': 'text', 'max_results': 5}, result=[{'result_id': 1, 'title': 
'DeepSeek R1 vs OpenAI o1: Which One is Better? - Analytics Vidhya', 
'description': "The DeepSeek R1 has arrived, and it's not just another AI 
model—it's a significant leap in AI capabilities, trained upon the previously 
released DeepSeek-V3-Base variant.With the full-fledged release of DeepSeek 
R1, it now stands on par with OpenAI o1 in both performance and flexibility. 
What makes it even more compelling is its open weight and MIT licensing, 
making it commercially ...", 'url': 'https://www.analyticsvidhya.com/blog/2025/
01/deepseek-r1-vs-openai-o1/'}, {'result_id': 2, 'title': 'DeepSeek-R1: 
Features, Use Cases, and Comparison with OpenAI', 'description': 'Where 
DeepSeek Shines: Mathematical reasoning and code generation, thanks to 
RL-driven CoT.; Where OpenAI Has an...
===============================================================================
'''
print(response.msgs[0].content)
# ruff: noqa: RUF001, E501
'''
===============================================================================
Below is an overview of DeepSeek R1, followed by a comparative analysis with OpenAI’s o3-mini model.

• What is DeepSeek R1?  
DeepSeek R1 is an AI model that represents a significant leap in reasoning and language capabilities. It stems from prior iterations like DeepSeek-V3-Base but incorporates additional supervised fine-tuning, enabling improvements in mathematical reasoning, logic, and code generation. One of its major selling points is its open nature—released with an open license (MIT) and open weights—making it highly attractive for research, customization, and commercial applications without the traditional licensing barriers. It has been praised for its affordability (with API usage that can be many times cheaper than some competing models) and has been shown on several benchmarks to hold its own against established models.

• What is OpenAI’s o3-mini?  
OpenAI’s o3-mini is part of OpenAI’s reasoning model series and is designed to deliver robust performance specifically in STEM areas such as science, mathematics, and coding. Announced as a response to emerging competition (including DeepSeek R1), o3-mini emphasizes cost efficiency while providing competitive reasoning capabilities. It’s integrated into the ChatGPT ecosystem (with availability on ChatGPT’s enterprise and education platforms) and positions itself as a compact yet powerful option that delivers high-quality reasoning at a lower cost than some earlier OpenAI versions.

• Comparing DeepSeek R1 and OpenAI o3-mini:

1. Performance & Capabilities  
  – Both models are geared toward advanced reasoning tasks, including problem-solving in STEM subjects and code generation.  
  – DeepSeek R1 has been lauded for its performance enhancements over previous iterations (especially in areas like mathematical reasoning) thanks to intensive fine-tuning, while independent evaluations have pitted it against other high-end models.  
  – OpenAI o3-mini is tuned to deliver high-quality reasoning with a focus on speed and cost-effectiveness, often showing particularly strong results in STEM benchmarks.

2. Accessibility and Licensing  
  – DeepSeek R1 is open source with an MIT license. Its openly available weights make it especially attractive for academic research, startups, or any developer who prefers customizable and transparent AI tools without prohibitive licensing fees.  
  – In contrast, OpenAI o3-mini is available via OpenAI’s platforms (such as ChatGPT and its API). Users generally access it through a subscription or pay-as-you-go model, with pricing structured to remain competitive against both previous OpenAI models and the emerging open-source alternatives.

3. Cost Efficiency  
  – DeepSeek R1’s open-source nature generally translates into lower entry costs, making it an economical choice for developers and companies that want to deploy advanced reasoning tools without high API fees.  
  – OpenAI o3-mini, although designed to be more cost-efficient compared to earlier OpenAI releases, is still part of a managed service infrastructure. According to industry reports, it is significantly cheaper (with some mentions of being up to 63% less expensive than some predecessors) and positioned as a competitive alternative in pricing, but it may still come with usage limits tied to subscription tiers.

4. Ecosystem Integration  
  – With DeepSeek R1, users have the freedom to run the model in customized environments or integrate it within open-source projects—this flexibility can drive innovation in experimental research or bespoke applications.  
  – OpenAI o3-mini benefits from OpenAI’s established ecosystem and integration into widely used platforms like ChatGPT Enterprise and Education. Its seamless integration means users can quickly leverage its capabilities without dealing with additional infrastructure setups.

In summary, while both DeepSeek R1 and OpenAI o3-mini aim to push forward the frontier of reasoning and STEM-focused AI models, they serve slightly different audiences. DeepSeek R1’s open-weight, open-license approach makes it ideal for those prioritizing versatility and low-cost research or customized product development. On the other hand, OpenAI o3-mini leverages OpenAI’s ecosystem to offer a highly optimized, cost-effective model that is integrated directly into widely used interfaces and platforms, providing a more out-of-the-box solution for end users and enterprise clients.
===============================================================================
'''
