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
# ruff: noqa: RUF001
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import WolframAlphaToolkit
from camel.types import ModelPlatformType, ModelType

system_message = "You're a helpful assistant"

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0.0},
)

tools = [WolframAlphaToolkit().query_wolfram_alpha]

agent = ChatAgent(
    system_message=system_message,
    model=model,
    tools=tools,
)

response = agent.step("What's 5 densest elemental metals")

print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])
'''
===============================================================================
The five densest elemental metals are:

1. Hassium (Hs) - 41 g/cm³
2. Meitnerium (Mt) - 37.4 g/cm³
3. Bohrium (Bh) - 37.1 g/cm³
4. Seaborgium (Sg) - 35.3 g/cm³
5. Darmstadtium (Ds) - 34.8 g/cm³

Tool calls:
[ToolCallingRecord(tool_name='query_wolfram_alpha', args={'query': 'densest 
elemental metals'}, result='1 | hassium | 41 g/cm^3 | \n2 | meitnerium | 37.4 
g/cm^3 | \n3 | bohrium | 37.1 g/cm^3 | \n4 | seaborgium | 35.3 g/cm^3 | \n5 | 
darmstadtium | 34.8 g/cm^3 |', tool_call_id='call_DNUzXQSQxAY3R71WMQXhKjBK')]
===============================================================================
'''

tools = [WolframAlphaToolkit().query_wolfram_alpha_step_by_step]

agent = ChatAgent(
    system_message=system_message,
    model=model,
    tools=tools,
)

response = agent.step("What's 5 densest elemental metals")

print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])
'''
===============================================================================
The five densest elemental metals are:

1. **Hassium (Hs)** - 41 g/cm³
2. **Meitnerium (Mt)** - 37.4 g/cm³
3. **Bohrium (Bh)** - 37.1 g/cm³
4. **Seaborgium (Sg)** - 35.3 g/cm³
5. **Darmstadtium (Ds)** - 34.8 g/cm³

These values represent their densities at standard conditions.

Tool calls:
[ToolCallingRecord(tool_name='query_wolfram_alpha_step_by_step', args=
{'query': '5 densest elemental metals'}, result={'query': '5 densest elemental 
metals', 'pod_info': [{'title': 'Input interpretation', 'description': '5 
densest metallic elements | by mass density', 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP961i0eg636ce4a7a95000064bh6be1f77a45af?
MSPStoreType=image/gif&s=10'}, {'title': 'Periodic table location', 
'description': None, 'image_url': 'https://www6b3.wolframalpha.com/Calculate/
MSP/MSP971i0eg636ce4a7a9500001668a66eh7ifgd6g?MSPStoreType=image/gif&s=10'}, 
{'title': 'Images', 'description': None, 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP981i0eg636ce4a7a95000025abi817gdd2964g?
MSPStoreType=image/gif&s=10'}, {'title': 'Basic elemental properties', 
'description': '| atomic symbol | atomic number\nhassium | Hs | 
108\nmeitnerium | Mt | 109\nbohrium | Bh | 107\nseaborgium | Sg | 
106\ndarmstadtium | Ds | 110\n | atomic mass | half-life\nhassium | 269 u | 67 
min\nmeitnerium | 277 u | 30 min\nbohrium | 270 u | 90 min\nseaborgium | 269 
u | 120 min\ndarmstadtium | 281 u | 4 min', 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP991i0eg636ce4a7a9500003263452b10d0d8f7?
MSPStoreType=image/gif&s=10'}, {'title': 'Result', 'description': '1 | 
hassium | 41 g/cm^3 | \n2 | meitnerium | 37.4 g/cm^3 | \n3 | bohrium | 37.1 g/
cm^3 | \n4 | seaborgium | 35.3 g/cm^3 | \n5 | darmstadtium | 34.8 g/cm^3 |', 
'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP1011i0eg636ce4a7a95000021433b3eei2283i7?MSPStoreType=image/gif&s=10'}, 
{'title': 'Material properties', 'description': 'mass density | median | 37.1 
g/cm^3\n | highest | 41 g/cm^3 (hassium)\n | lowest | 34.8 g/cm^3 
(darmstadtium)\n | distribution | \n(properties at standard conditions)', 
'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP1031i0eg636ce4a7a95000012h4aa1fg10h84eg?MSPStoreType=image/gif&s=10'}, 
{'title': 'Atomic properties', 'description': 'term symbol | all | ^3D_3 | ^4F_
(9/2) | ^5D_0 | ^5D_4 | ^6S_(5/2)\n(electronic ground state properties)', 
'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP1051i0eg636ce4a7a95000024dii0bd852f9bib?MSPStoreType=image/gif&s=10'}, 
{'title': 'Abundances', 'description': 'crust abundance | median | 0 mass%\n | 
highest | 0 mass% (5 elements)\n | lowest | 0 mass% (5 elements)\nhuman 
abundance | median | 0 mass%\n | highest | 0 mass% (5 elements)\n | lowest | 0 
mass% (5 elements)', 'image_url': 'https://www6b3.wolframalpha.com/Calculate/
MSP/MSP1061i0eg636ce4a7a9500005iagh7h9413cc095?MSPStoreType=image/gif&s=10'}, 
{'title': 'Nuclear properties', 'description': 'half-life | median | 67 
min\n | highest | 120 min (seaborgium)\n | lowest | 4 min (darmstadtium)\n | 
distribution | \nspecific radioactivity | highest | 6.123×10^6 TBq/g 
(darmstadtium)\n | lowest | 223871 TBq/g (seaborgium)\n | median | 446085 TBq/
g', 'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP1081i0eg636ce4a7a9500001ae7307034bg8h9a?MSPStoreType=image/gif&s=10'}, 
{'title': 'Wikipedia page hits history', 'description': None, 'image_url': 
'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP1101i0eg636ce4a7a9500003aeef8d2fi6ih413?MSPStoreType=image/gif&s=10'}], 
'final_answer': '1 | hassium | 41 g/cm^3 | \n2 | meitnerium | 37.4 g/cm^3 | 
\n3 | bohrium | 37.1 g/cm^3 | \n4 | seaborgium | 35.3 g/cm^3 | \n5 | 
darmstadtium | 34.8 g/cm^3 |', 'steps': {}}, 
tool_call_id='call_e6gApIh8ohCARb4fb9WDxEsq')]
===============================================================================
'''

tools = [WolframAlphaToolkit().query_wolfram_alpha_llm]

agent = ChatAgent(
    system_message=system_message,
    model=model,
    tools=tools,
)

response = agent.step("What's 10 densest elemental metals")

print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])
'''
===============================================================================
The 10 densest elemental metals, measured by mass density, are:

1. **Hassium (Hs)** - 41 g/cm³
2. **Meitnerium (Mt)** - 37.4 g/cm³
3. **Bohrium (Bh)** - 37.1 g/cm³
4. **Seaborgium (Sg)** - 35.3 g/cm³
5. **Darmstadtium (Ds)** - 34.8 g/cm³
6. **Dubnium (Db)** - 29.3 g/cm³
7. **Roentgenium (Rg)** - 28.7 g/cm³
8. **Rutherfordium (Rf)** - 23.2 g/cm³
9. **Osmium (Os)** - 22.59 g/cm³
10. **Iridium (Ir)** - 22.56 g/cm³

These values represent the density of each metal at standard conditions.

Tool calls:
[ToolCallingRecord(tool_name='query_wolfram_alpha_llm', args={'query': '10 
densest elemental metals'}, result='Query:\n"10 densest elemental 
metals"\n\nInput interpretation:\n10 densest metallic elements | by mass 
density\n\nBasic elemental properties:\natomic symbol | all | Bh | Db | Ds | 
Hs | Ir | Mt | Os | Rf | Rg | Sg\natomic number | median | 106.5\n | highest | 
111 (roentgenium)\n | lowest | 76 (osmium)\n | distribution | \natomic mass | 
median | 269 u\n | highest | 282 u (roentgenium)\n | lowest | 190.23 u (osmium)
\n | distribution | \nhalf-life | median | 78 min\n | highest | 13 h 
(rutherfordium)\n | lowest | 4 min (darmstadtium)\n | distribution | 
\n\nResult:\n1 | hassium | 41 g/cm^3 | \n2 | meitnerium | 37.4 g/cm^3 | \n3 | 
bohrium | 37.1 g/cm^3 | \n4 | seaborgium | 35.3 g/cm^3 | \n5 | darmstadtium | 
34.8 g/cm^3 | \n6 | dubnium | 29.3 g/cm^3 | \n7 | roentgenium | 28.7 g/cm^3 | 
\n8 | rutherfordium | 23.2 g/cm^3 | \n9 | osmium | 22.59 g/cm^3 | \n10 | 
iridium | 22.56 g/cm^3 | \n\nThermodynamic properties:\nphase at STP | all | 
solid\n(properties at standard conditions)\n\nMaterial properties:\nmass 
density | median | 32.1 g/cm^3\n | highest | 41 g/cm^3 (hassium)\n | lowest | 
22.56 g/cm^3 (iridium)\n | distribution | \n(properties at standard conditions)
\n\nReactivity:\nvalence | median | 6\n | highest | 7 (bohrium)\n | lowest | 4 
(rutherfordium)\n | distribution | \n\nAtomic properties:\nterm symbol | all | 
^2S_(1/2) | ^3D_3 | ^3F_2 | ^4F_(3/2) | ^4F_(9/2) | ^5D_0 | ^5D_4 | ^6S_(5/2)\n
(electronic ground state properties)\n\nAbundances:\ncrust abundance | 
median | 0 mass%\n | highest | 1.8×10^-7 mass% (osmium)\n | lowest | 0 mass% 
(8 elements)\nhuman abundance | median | 0 mass%\n | highest | 0 mass% (8 
elements)\n | lowest | 0 mass% (8 elements)\n\nNuclear 
properties:\nhalf-life | median | 78 min\n | highest | 13 h (rutherfordium)
\n | lowest | 4 min (darmstadtium)\n | distribution | \nspecific 
radioactivity | highest | 6.123×10^6 TBq/g (darmstadtium)\n | lowest | 33169 
TBq/g (rutherfordium)\n | median | 366018 TBq/g\n | distribution | \n\nWolfram|
Alpha website result for "10 densest elemental metals":\nhttps://www6b3.
wolframalpha.com/input?i=10+densest+elemental+metals', 
tool_call_id='call_b2FBtvFoRpP17UPOXDEvQg5Q')]
===============================================================================
'''
