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
    query="solve 3x-7=11", is_detailed=False
)

print(res_simple)
'''
===============================================================================
x = 6
===============================================================================
'''

res_detailed = WolframAlphaToolkit().query_wolfram_alpha(
    query="solve 3x-7=11", is_detailed=True
)

print(res_detailed)
'''
===============================================================================
{'query': 'solve 3x-7=11', 'pod_info': [{'title': 'Input interpretation',
'description': 'solve 3 x - 7 = 11', 'image_url': 'https://www6b3.wolframalpha.
com/Calculate/MSP/MSP37741a3dc67f338579ff00003fih94dg39300iaf?
MSPStoreType=image/gif&s=18'}, {'title': 'Result', 'description': 'x = 6',
'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP37751a3dc67f338579ff00001dg4gbdcd0f10i3f?MSPStoreType=image/gif&s=18'},
{'title': 'Plot', 'description': None, 'image_url': 'https://www6b3.
wolframalpha.com/Calculate/MSP/MSP37761a3dc67f338579ff0000374484g95bh3ah3e?
MSPStoreType=image/gif&s=18'}, {'title': 'Number line', 'description': None,
'image_url': 'https://www6b3.wolframalpha.com/Calculate/MSP/
MSP37771a3dc67f338579ff00005573c3a87ahg8dbc?MSPStoreType=image/gif&s=18'}],
'final_answer': 'x = 6', 'steps': {'step1': 'Isolate terms with x to the left
hand side.\nAdd 7 to both sides:\n3 x + (7 - 7) = 7 + 11', 'step2': 'Look for
the difference of two identical terms.\n7 - 7 = 0:\n3 x = 11 + 7', 'step3':
'Evaluate 11 + 7.\n11 + 7 = 18:\n3 x = 18', 'step4': 'Divide both sides by a
constant to simplify the equation.\nDivide both sides of 3 x = 18 by 3:\n(3 x)/
3 = 18/3', 'step5': 'Any nonzero number divided by itself is one.\n3/3 = 1:\nx
= 18/3', 'step6': 'Reduce 18/3 to lowest terms. Start by finding the greatest
common divisor of 18 and 3.\nThe greatest common divisor of 18 and 3 is 3, so
factor out 3 from both the numerator and denominator: 18/3 = (3x6)/(3x1) = 3/3
x 6 = 6\nAnswer: | \n | x = 6'}}
===============================================================================
'''

res_llm = WolframAlphaToolkit().query_wolfram_llm(query="solve 3x-7=11")

print(res_llm)

'''
===============================================================================
'Query:\n"solve 3x-7=11"\n\nInput interpretation:\nsolve 3 x - 7 = 11\n\nResult
:\nx = 6\n\nPlot:\nimage: https://www6b3.wolframalpha.com/Calculate/MSP/MSP6802
0g1bg1ih5hce47h000016g8h3d8220352g2?MSPStoreType=image/png&s=2\nWolfram 
Language code: Plot[{-7 + 3 x, 11}, {x, -9., 9.}]\n\nNumber line:\nimage: 
https://www6b3.wolframalpha.com/Calculate/MSP/MSP68120g1bg1ih5hce47h000047d112
d53f34d535?MSPStoreType=image/png&s=2\nWolfram Language code: NumberLinePlot[x
== 6, x]\n\nWolfram|Alpha website result for "solve 3x-7=11":\nhttps://www6b3
.wolframalpha.com/input?i=solve+3x-7%3D11'
===============================================================================
'''
