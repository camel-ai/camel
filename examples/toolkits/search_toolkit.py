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

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.toolkits import FunctionTool, SearchToolkit

res_simple = SearchToolkit().query_wolfram_alpha(
    query="solve 3x-7=11", is_detailed=False
)

print(res_simple)
'''
===============================================================================
x = 6
===============================================================================
'''

res_detailed = SearchToolkit().query_wolfram_alpha(
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

res_brave = SearchToolkit().search_brave(
    q="What is the weather in Tokyo?",
    search_lang="en",
)
print(res_brave)

# Example with ChatAgent using the Brave search engine

agent = ChatAgent(
    system_message="""You are a helpful assistant that can use brave search 
        engine to answer questions.""",
    tools=[FunctionTool(SearchToolkit().search_brave)],
)

usr_msg = "What is the temperature in Tokyo?"

response = agent.step(input_message=usr_msg, response_format=None)

print(response.msgs[0].content)
'''
The current temperature in Tokyo can be found on various weather websites. 
Here are a couple of reliable sources where you can check the latest weather 
conditions:

1. [AccuWeather - Tokyo Current Weather](https://www.accuweather.com/en/jp/tokyo/226396/current-weather/226396)
2. [Time and Date - Tokyo Weather](https://www.timeanddate.com/weather/japan/tokyo)

You can visit these links to get the most up-to-date temperature and weather 
conditions in Tokyo.
'''

search_linkup_response = SearchToolkit().search_linkup(
    query="Can you tell me which women were awared the Physics Nobel Prize",
    depth="standard",
    output_type="searchResults",
)

print(search_linkup_response)
"""
{'results': [{'type': 'text', 'name': 'Physics Nobel Prizes awarded to women | 
Scientia News', 'url': 'https://www.scientianews.org/
physics-nobel-prize-winners', 'content': 'The next female Nobel Prize in 
Physics award winner wouldn't be until another half-century later, with Donna 
Strickland. Strickland was awarded the Prize for her work on chirped pulse 
amplification and its applications. Although the research itself was published 
in 1985, she didn't receive the award until 2018.'}, {'type': 'text', 'name': 
'The 60 Women Who Have Won the Nobel Prize - Stacker', 'url': 'https://stacker.
com/history/60-women-who-have-won-nobel-prize', 'content': '- Award: Nobel 
Prize in Physics - Year: 1963. Maria Goeppert-Mayer was born in Germany. After 
she married, she migrated to America, where she worked on an American atom 
bomb project during World War II. Her work uncovered important discoveries 
about nuclear structure, and Goeppert-Mayer is one of only four women to win 
the Nobel Prize in physics.'}, {'type': 'text', 'name': 'Nobel Prize awarded 
women - NobelPrize.org', 'url': 'https://www.nobelprize.org/prizes/lists/
nobel-prize-awarded-women/', 'content': 'The Nobel Prize and the Sveriges 
Riksbank Prize in Economic Sciences in Memory of Alfred Nobel have been 
awarded to women 66 times between 1901 and 2024. Only one woman, Marie Curie, 
has been honoured twice, with the Nobel Prize in Physics 1903 and the Nobel 
Prize in Chemistry 1911. This means that 65 women in total have been awarded 
the Nobel ...'}, {'type': 'text', 'name': 'Women who changed science - The 
Nobel Prize', 'url': 'https://www.nobelprize.org/womenwhochangedscience/
stories', 'content': 'Nobel Prize in Physics 1903 Nobel Prize in Chemistry 
1911. MARIE CURIE. Read her story. Nobel Prize in Physiology or Medicine 1988. 
GERTRUDE B. ELION. Read her story. Nobel Prize in Physiology or Medicine 1988. 
GERTRUDE B. ELION. Read her story. Nobel Prize in Physics 1963. MARIA GOEPPERT 
MAYER. Read her story.'}, {'type': 'text', 'name': 'List of female Nobel 
laureates - Wikipedia', 'url': 'https://en.wikipedia.org/wiki/
List_of_female_Nobel_laureates', 'content': "The most recent women to be 
awarded a Nobel Prize were Han Kang in Literature (2024), Claudia Goldin in 
Economics, Narges Mohammadi for Peace, Anne L'Huillier in Physics and Katalin 
Karikó in Physiology or Medicine (2023), Annie Ernaux in Literature and 
Carolyn R. Bertozzi for Chemistry (2022), Maria Ressa for Peace (2021), Louise 
Glück in ..."}, {'type': 'text', 'name': 'Only 5 women have won the Nobel 
Prize in physics—recent winners share ...', 'url': 'https://phys.org/news/
2024-10-women-won-nobel-prize-physics.html', 'content': 'Out of 225 people 
awarded the Nobel Prize in physics, only five have been women. This is a very 
small number, and certainly smaller than 50%—the percent of women in the human 
population.'}, {'type': 'text', 'name': 'All These Women Won Science Nobel 
Prizes - The Stemettes Zine', 'url': 'https://stemettes.org/zine/articles/
nobel-prize-women/', 'content': 'Currently, only 17% of Nobel Prize winners 
are women in the Science categories. So here we are celebrating all the 
amazing women who have Nobel Prizes for their Science research. ... & Physics 
(1903) Marie and her husband were awarded the Nobel Prize for Physics in 1903, 
for their study into the spontaneous radiation discovered by Becquerel. In ...
'}, {'type': 'text', 'name': 'These Are the 57 Women Who Have Won the Nobel 
Prize', 'url': 'https://www.newsweek.com/
these-are-57-women-who-have-won-nobel-prize-1538702', 'content': 'Getty Images/
Hulton-Deutsch Collection/CORBIS Marie Curie (born Skłodowska) - Award: Nobel 
Prize in Physics - Year: 1903. Marie Curie, who was the first woman to win a 
Nobel Prize, coined the ...'}, {'type': 'text', 'name': 'Anne L'Huillier - 
Banquet speech - NobelPrize.org', 'url': 'https://www.nobelprize.org/prizes/
physics/2023/lhuillier/speech/', 'content': 'The Nobel Prize in Physics 2023 
was awarded to Pierre Agostini, Ferenc Krausz and Anne L'Huillier "for 
experimental methods that generate attosecond pulses of light for the study of 
electron dynamics in matter" ... 120 years ago, Marie Skłodowska Curie was the 
first woman to be awarded the Nobel Prize in Physics. I am the fifth. For 
more ...'}, {'type': 'text', 'name': 'Facts on the Nobel Prize in Physics - 
NobelPrize.org', 'url': 'https://www.nobelprize.org/prizes/facts/
facts-on-the-nobel-prize-in-physics/', 'content': 'List of all female Nobel 
Prize laureates. Multiple Nobel Prize laureates in physics. John Bardeen is 
the only person who has received the Nobel Prize in Physics twice, year 1956 
and 1972 . Marie Curie was awarded the Nobel Prize twice, once in physics 1903 
and once in chemistry 1911.. See the list of multiple Nobel Prize laureates 
within other Nobel Prize categories here'}]}
"""

search_linkup_response = SearchToolkit().search_linkup(
    query="Can you tell me which women were awared the Physics Nobel Prize",
    depth="standard",
    output_type="sourcedAnswer",
)

print(search_linkup_response)
"""
{'answer': "The women who have been awarded the Nobel Prize in Physics are: 1. 
Marie Curie - 1903 2. Maria Goeppert Mayer - 1963 3. Donna Strickland - 2018 
4. Anne L'Huillier - 2023", 'sources': [{'name': 'Nobel Prize awarded women - 
NobelPrize.org', 'url': 'https://www.nobelprize.org/prizes/lists/
nobel-prize-awarded-women/', 'snippet': 'The Nobel Prize and the Sveriges 
Riksbank Prize in Economic Sciences in Memory of Alfred Nobel have been 
awarded to women 66 times between 1901 and 2024.'}, {'name': 'Physics Nobel 
Prizes awarded to women | Scientia News', 'url': 'https://www.scientianews.org/
physics-nobel-prize-winners', 'snippet': 'The next female Nobel Prize in 
Physics award winner wouldn't be until another half-century later, with Donna 
Strickland.'}, {'name': 'List of female Nobel laureates - Wikipedia', 'url': 
'https://en.wikipedia.org/wiki/List_of_female_Nobel_laureates', 'snippet': 
"The most recent women to be awarded a Nobel Prize were Han Kang in Literature 
(2024), Claudia Goldin in Economics, Narges Mohammadi for Peace, Anne 
L'Huillier in Physics and Katalin Karikó in Physiology or Medicine (2023)."}]}
(camel-ai-py3.10) ruihan@RuideMac-mini camel % 
"""


class PersonInfo(BaseModel):
    # Basic company information
    name: str = ""  # Company name
    description: str = ""


search_linkup_response = SearchToolkit().search_linkup(
    query="Can you tell me which women were awared the Physics Nobel Prize",
    depth="standard",
    output_type="structured",
    structured_output_schema=PersonInfo,
)
print(search_linkup_response)

"""
{'name': 'Female Nobel Prize Winners in Physics', 'description': 'The women 
awarded the Nobel Prize in Physics include: 1. Marie Curie (1903) 2. Maria 
Goeppert-Mayer (1963) 3. Donna Strickland (2018) 4. (4th winner not mentioned 
in the provided data) 5. (5th winner not mentioned in the provided data). Less 
than 5 women have won the Nobel Prize in Physics out of 225 total laureates.'}
"""
