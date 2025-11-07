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
from camel.toolkits import SearchToolkit, ToolkitMessageIntegration

message_integration = ToolkitMessageIntegration()

wiki_search = SearchToolkit().search_wiki

# Add messaging capabilities to specific tools
enhanced_search = message_integration.register_functions([wiki_search])

chat_agent = ChatAgent(
    system_message="You are a helpful assistant that can search the web.",
    tools=enhanced_search,
)

response = chat_agent.step(
    "What is Scaling laws? You must use the search tool to find the answer."
)

print(response.msg.content)

"""
===============================================================================
Agent Message:
Information about Scaling laws
Searching for detailed information about Scaling laws from Wikipedia.

Scaling laws refer to functional relationships between two quantities where a 
relative change in one quantity results in a relative change in the other 
quantity, proportional to the change raised to a constant exponent. This is 
known as a power law, where one quantity varies as a power of another, and the 
change is independent of the initial size of those quantities.

For example, the area of a square has a power law relationship with the length 
of its side: if the side's length is doubled, the area is multiplied by 2², 
and if tripled, the area is multiplied by 3².

Scaling laws can be observed in numerous natural and human-made phenomena, 
such as the sizes of craters on the moon, sizes of solar flares, cloud sizes, 
foraging patterns of species, frequencies of words in languages, and many 
more. These empirical distributions follow a power law over a range of 
magnitudes but cannot fit a power law for all values as it would imply 
arbitrarily large or small values.
===============================================================================
"""
