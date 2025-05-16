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
MSP366132eb05g1g302ac200006af0d8f282hd4a5h?MSPStoreType=image/gif&s=1'}, 
{'title': 'Periodic table location', 'description': None, 'image_url': 
'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP367132eb05g1g302ac2000023743068d984gci9?MSPStoreType=image/gif&s=1'}, 
{'title': 'Images', 'description': None, 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP368132eb05g1g302ac200004eada51igi7h1bbd?
MSPStoreType=image/gif&s=1'}, {'title': 'Basic elemental properties', 
'description': 'atomic symbol | all | Bh | Db | Ds | Hs | Ir | Mt | Os | Rf | 
Rg | Sg\natomic number | median | 106.5\n | highest | 111 (roentgenium)\n | 
lowest | 76 (osmium)\n | distribution | \natomic mass | median | 269 u\n | ...
===============================================================================
'''

res_llm = WolframAlphaToolkit().query_wolfram_llm(
    query="10 densest elemental metals"
)

print(res_llm)
