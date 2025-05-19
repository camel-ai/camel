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
from camel.models import ModelFactory
from camel.toolkits import WolframAlphaToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

res_simple = WolframAlphaToolkit().query_wolfram_alpha(
    query="10 densest elemental metals", is_detailed=False
)

print(res_simple)
'''
===============================================================================
1 | hassium | 41 g/cm^3 | 
2 | meitnerium | 37.4 g/cm^3 | 
3 | bohrium | 37.1 g/cm^3 | 
4 | seaborgium | 35.3 g/cm^3 | 
5 | darmstadtium | 34.8 g/cm^3 | 
⋮ | | |
===============================================================================
'''

res_detailed = WolframAlphaToolkit().query_wolfram_alpha(
    query="10 densest elemental metals", is_detailed=True
)

print(res_detailed)
'''
===============================================================================
{'query': '10 densest elemental metals', 'pod_info': [{'title': 'Input 
interpretation', 'description': '10 densest metallic elements | by mass 
density', 'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP80615372a2bchig48380000471fi5d51ii9552i?MSPStoreType=image/gif&s=16'}, 
{'title': 'Periodic table location', 'description': None, 'image_url': 
'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP80715372a2bchig483800001902583db73681b0?MSPStoreType=image/gif&s=16'}, 
{'title': 'Images', 'description': None, 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP80815372a2bchig483800001dif7af61710hcc8?
MSPStoreType=image/gif&s=16'}, {'title': 'Basic elemental properties', 
'description': 'atomic symbol | all | Bh | Db | Ds | Hs | Ir | Mt | Os | Rf | 
Rg | Sg\natomic number | median | 106.5\n | highest | 111 (roentgenium)\n | 
lowest | 76 (osmium)\n | distribution | \natomic mass | median | 269 u\n | 
highest | 282 u (roentgenium)\n | lowest | 190.23 u (osmium)\n | 
distribution | \nhalf-life | median | 78 min\n | highest | 13 h (rutherfordium)
\n | lowest | 4 min (darmstadtium)\n | distribution |', 'image_url': 'https://
www6b3.wolframalpha.com/Calculate/MSP/
MSP80915372a2bchig4838000011cc2fb989c538fa?MSPStoreType=image/gif&s=16'}, 
{'title': 'Result', 'description': '1 | hassium | 41 g/cm^3 | \n2 | 
meitnerium | 37.4 g/cm^3 | \n3 | bohrium | 37.1 g/cm^3 | \n4 | seaborgium | 35.
3 g/cm^3 | \n5 | darmstadtium | 34.8 g/cm^3 | \n⋮ | | |', 'image_url': 
'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP81115372a2bchig4838000036fgd7gggf347gd7?MSPStoreType=image/gif&s=16'}, 
{'title': 'Thermodynamic properties', 'description': 'phase at STP | all | 
solid\n(properties at standard conditions)', 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP81315372a2bchig483800001gaa02a7439934fd?
MSPStoreType=image/gif&s=16'}, {'title': 'Material properties', 'description': 
'mass density | median | 32.1 g/cm^3\n | highest | 41 g/cm^3 (hassium)\n | 
lowest | 22.56 g/cm^3 (iridium)\n | distribution | \n(properties at standard 
conditions)', 'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP81415372a2bchig48380000408d23ifc2b056f3?MSPStoreType=image/gif&s=16'}, 
{'title': 'Reactivity', 'description': 'valence | median | 6\n | highest | 7 
(bohrium)\n | lowest | 4 (rutherfordium)\n | distribution |', 'image_url': 
'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP81615372a2bchig483800003ih6ci3c0fab279f?MSPStoreType=image/gif&s=16'}, 
{'title': 'Atomic properties', 'description': 'term symbol | all | ^2S_(1/2) | 
^3D_3 | ^3F_2 | ^4F_(3/2) | ^4F_(9/2) | ^5D_0 | ^5D_4 | ^6S_(5/2)\n(electronic 
ground state properties)', 'image_url': 'https://www6b3.wolframalpha.com/
Calculate/MSP/MSP81715372a2bchig48380000421b78e47ddc5de0?MSPStoreType=image/
gif&s=16'}, {'title': 'Abundances', 'description': 'crust abundance | median | 
0 mass%\n | highest | 1.8×10^-7 mass% (osmium)\n | lowest | 0 mass% (8 
elements)\nhuman abundance | median | 0 mass%\n | highest | 0 mass% (8 
elements)\n | lowest | 0 mass% (8 elements)', 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP81815372a2bchig48380000399cbba92d566dac?
MSPStoreType=image/gif&s=16'}, {'title': 'Nuclear properties', 'description': 
'half-life | median | 78 min\n | highest | 13 h (rutherfordium)\n | lowest | 4 
min (darmstadtium)\n | distribution | \nspecific radioactivity | highest | 6.
123×10^6 TBq/g (darmstadtium)\n | lowest | 33169 TBq/g (rutherfordium)\n | 
median | 366018 TBq/g\n | distribution |', 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP82015372a2bchig4838000023ga94gh9ihhhefb?
MSPStoreType=image/gif&s=16'}], 'final_answer': '1 | hassium | 41 g/cm^3 | 
\n2 | meitnerium | 37.4 g/cm^3 | \n3 | bohrium | 37.1 g/cm^3 | \n4 | 
seaborgium | 35.3 g/cm^3 | \n5 | darmstadtium | 34.8 g/cm^3 | \n⋮ | | |', 
'steps': {}}
===============================================================================
'''

res_llm = WolframAlphaToolkit().query_wolfram_alpha_llm(
    query="10 densest elemental metals"
)

print(res_llm)
'''
===============================================================================
Query:
"10 densest elemental metals"

Input interpretation:
10 densest metallic elements | by mass density

Periodic table location:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7491501b77df5bhaaci0000454bh00124146c46?MSPStoreType=image/png&s=11

Images:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7501501b77df5bhaaci00005i7f8c1e0a7hebi0?MSPStoreType=image/png&s=11
Wolfram Language code: Dataset[EntityValue[{Entity["Element", "Hassium"], 
Entity["Element", "Meitnerium"], Entity["Element", "Bohrium"], Entity
["Element", "Seaborgium"], Entity["Element", "Darmstadtium"], Entity
["Element", "Dubnium"], Entity["Element", "Roentgenium"], Entity["Element", 
"Rutherfordium"], Entity["Element", "Osmium"], Entity["Element", "Iridium"]}, 
EntityProperty["Element", "Image"], "EntityAssociation"]]

Basic elemental properties:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7511501b77df5bhaaci00004h1d0hfh1hh25agh?MSPStoreType=image/png&s=11

Result:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7521501b77df5bhaaci00002746fi9b03h6c9ad?MSPStoreType=image/png&s=11

Thermodynamic properties:
phase at STP | all | solid
(properties at standard conditions)

Material properties:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7531501b77df5bhaaci000044egfd69a7iegeb1?MSPStoreType=image/png&s=11

Reactivity:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7541501b77df5bhaaci00005g6dh3eg2301d31g?MSPStoreType=image/png&s=11

Atomic properties:
term symbol | all | ^2S_(1/2) | ^3D_3 | ^3F_2 | ^4F_(3/2) | ^4F_(9/2) | 
^5D_0 | ^5D_4 | ^6S_(5/2)
(electronic ground state properties)

Abundances:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7551501b77df5bhaaci00003832d90bfgacadb8?MSPStoreType=image/png&s=11

Nuclear properties:
image: https://www6b3.wolframalpha.com/Calculate/MSP/
MSP7561501b77df5bhaaci00002b2e7b10873hfgge?MSPStoreType=image/png&s=11

Wolfram|Alpha website result for "10 densest elemental metals":
https://www6b3.wolframalpha.com/input?i=10+densest+elemental+metals
===============================================================================
'''
