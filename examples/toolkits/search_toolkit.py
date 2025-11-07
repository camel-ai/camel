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
"""
===============================================================================
The current temperature in Tokyo can be found on various weather websites.
Here are a couple of reliable sources where you can check the latest weather
conditions:

1. [AccuWeather - Tokyo Current Weather](https://www.accuweather.com/en/jp/tokyo/226396/current-weather/226396)
2. [Time and Date - Tokyo Weather](https://www.timeanddate.com/weather/japan/tokyo)

You can visit these links to get the most up-to-date temperature and weather
conditions in Tokyo.
===============================================================================
"""
search_linkup_response = SearchToolkit().search_linkup(
    query="Can you tell me which women were awarded the Physics Nobel Prize",
    depth="standard",
    output_type="searchResults",
)

print(search_linkup_response)
"""
===============================================================================
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
===============================================================================
"""

search_linkup_response = SearchToolkit().search_linkup(
    query="Can you tell me which women were awarded the Physics Nobel Prize",
    depth="standard",
    output_type="sourcedAnswer",
)

print(search_linkup_response)
"""
===============================================================================
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
===============================================================================
"""


class PersonInfo(BaseModel):
    # Basic company information
    name: str = ""  # Company name
    description: str = ""


search_linkup_response = SearchToolkit().search_linkup(
    query="Can you tell me which women were awarded the Physics Nobel Prize",
    depth="standard",
    output_type="structured",
    structured_output_schema=PersonInfo,
)
print(search_linkup_response)

"""
===============================================================================
{'name': 'Female Nobel Prize Winners in Physics', 'description': 'The women
awarded the Nobel Prize in Physics include: 1. Marie Curie (1903) 2. Maria
Goeppert-Mayer (1963) 3. Donna Strickland (2018) 4. (4th winner not mentioned
in the provided data) 5. (5th winner not mentioned in the provided data). Less
than 5 women have won the Nobel Prize in Physics out of 225 total laureates.'}
===============================================================================
"""

search_bocha_response = SearchToolkit().search_bocha(
    query="阿里巴巴2024年的esg报告",
    freshness="noLimit",
    summary=False,
    count=10,
)
print(search_bocha_response)

"""
===============================================================================
{"_type":"SearchResponse","queryContext":{"originalQuery":"阿里巴巴2024年的esg报
告"},"webPages":{"webSearchUrl":"","totalEstimatedMatches":8912791,"value":[
{"id":None,"name":"阿里巴巴发布2024年ESG报告持续推进减碳与数字化普惠","url":"ht
tps://www.alibabagroup.com/document-1752073403914780672","displayUrl":"htt
ps://www.alibabagroup.com/document-1752073403914780672","snippet":"阿里巴巴
集团发布《2024财年环境、社会和治理(ESG)报告》(下称"报告"),详细分享过去一年在ESG各方面取
得的进展。报告显示,阿里巴巴扎实推进减碳举措,全集团自身运营净碳排放和价值链碳...","siteName"
:"www.alibabagroup.com","siteIcon":"https://th.bochaai.com/favicon?domain_url=
https://www.alibabagroup.com/document-1752073403914780672","dateLastCrawled":
"2024-07-22T00:00:00Z","cachedPageUrl":None,"language":None,"isFamilyFriendly"
:None,"isNavigational":None},],"someResultsRemoved":true},"images":{"id":None,
"readLink":None,"webSearchUrl":None,"value":[{"webSearchUrl":None,"name":None,
"thumbnailUrl":"http://q7.itc.cn/q_70/images01/20240726/ee26d6fa8658472d8b4c5
e7236b1640a.png","datePublished":None,"contentUrl":"http://q7.itc.cn/q_70/im
ages01/20240726/ee26d6fa8658472d8b4c5e7236b1640a.png","hostPageUrl":"https://
m.sohu.com/a/796245119_121713887/?pvid=000115_3w_a","contentSize":None,"enco
dingFormat":None,"hostPageDisplayUrl":"https://m.sohu.com/a/796245119_121713887
/?pvid=000115_3w_a","width":1285,"height":722,"thumbnail":None}],"isFamilyFrien
dly":None},"videos":None}
===============================================================================
"""


agent = ChatAgent(
    system_message="""You are a helpful assistant that can use baidu search
        engine to answer questions.""",
    tools=[FunctionTool(SearchToolkit().search_baidu)],
)

usr_msg = "今天北京的天气如何"

response = agent.step(input_message=usr_msg, response_format=None)

print(response.msgs[0].content)

"""
===============================================================================
今天北京的天气信息可以通过以下链接查看:

1. [中国天气网 - 北京天气预报](http://www.baidu.com/link?
url=AJhE9PhEO3TmkJ70CUcRsR3NVB3m6wxN5Imdp0ZVsEBK1t8YhtM6YMxrQy3_vRN6dJv4FLHkBCe
fZURnzHTm9gio-dS4-4MwGVgJe40m7prOoggce2eB0h-3DsllbKMm)
2. [中国天气网 - 北京天气预报](http://www.baidu.com/link?
url=1vhNOfl9tV65_104GMQbDnU_fdCZPXDV2BtTJelxdd6isdSZjAHvtoXqOWG3n7D1N-m9zAmOhQG
c-jEGqiXe9K)
3. [中国天气网 - 北京天气预报](http://www.baidu.com/link?
url=Q0URfpodXDpUe1TKBPpToKIyIuCcjSGUR5jorx81g8Pni5XH-Tbc6AXMa7EwCWjBG3jysTZb43S
6ZCsJOKvPw2EbIlQ_bMu42-5sCraqXlS)
4. [中国天气网 - 北京天气预报一周](http://www.baidu.com/link?
url=TtFe8QryJFuwX1kx50YF5WijRcd2TMJRhPudDQvqW7TG4siah68gUZd_frsVWPi1xkYvrxoYL87
QMH0wSjDYOq)

请点击链接查看详细的天气预报信息。
===============================================================================
"""

bing_call_agent = ChatAgent(
    system_message="""You are a helpful assistant that can use baidu search
        engine to answer questions.""",
    tools=[FunctionTool(SearchToolkit().search_bing)],
)

bing_usr_msg = "帮忙查询巴黎圣母院最新修复进展"

response = bing_call_agent.step(
    input_message=bing_usr_msg, response_format=None
)

print(response.msgs[0].content)

"""
===============================================================================
以下是关于巴黎圣母院最新修复进展的一些信息:

1. **时隔4年,灾后余生的巴黎圣母院即将重生** -
[知乎](https://zhuanlan.zhihu.com/p/619405504)

2. **历时4年,耗资70亿,被烧塌的巴黎圣母院修好了!!** -
[腾讯网](https://news.qq.com/rain/a/20231018A0329F00)

3. **一票难求!巴黎圣母院重新开放!5年修复离不开来自东方的支持** -
[新浪财经](https://finance.sina.com.cn/wm/2024-12-08/doc-incyumnp3384392.shtml)

4. **巴黎圣母院浴火重生!建筑学者:勘探报告近3000页,修复工作复杂** -
[腾讯网](https://news.qq.com/rain/a/20241208A05Q9K00)

这些链接提供了关于巴黎圣母院修复的详细信息和最新进展。
===============================================================================
"""

# Example using Exa search
exa_response = SearchToolkit().search_exa(
    query="What is CAMEL-AI?",
    category="github",
    num_results=1,
    text=True,
)

print(exa_response)

# Example with ChatAgent using Exa search
exa_agent = ChatAgent(
    system_message="""You are a helpful assistant that can use Exa search 
        engine to find the latest research papers.""",
    tools=[FunctionTool(SearchToolkit().search_exa)],
)

usr_msg = "What are the latest developments in quantum error correction?"

response = exa_agent.step(input_message=usr_msg, response_format=None)

print(response.msgs[0].content)
"""
===============================================================================
Here are some of the latest developments in quantum error correction:

1. **Suppressing Quantum Errors by Scaling a Surface Code Logical Qubit**  
- **Published Date**: February 22, 2023  
- **Authors**: Google Quantum AI  
- **Summary**: This work reports on a 72-qubit superconducting device 
implementing  49-qubit distance-5 surface code, improving the performance over
a dist-3 code. The research demonstrates how scaling error-correcting codes
can lead to significant reductions in logical error rates.  
- **Link**: [Read paper](https://www.nature.com/articles/s41586-022-05434-1)

![Image](https://media.springernature.com/m685/springer-static/image/art%3A10.
1038%2Fs41586-022-05434-1/MediaObjects/41586_2022_5434_Fig1_HTML.png)

2. **Increasing Error Tolerance in Quantum Computers with Dynamic Bias**  
- **Published Date**: March 28, 2023  
- **Authors**: H'ector Bomb'in, C. Dawson, Naomi H. Nickerson, M. Pant
- **Summary**: This study introduces a method for dynamically arranging error
biases to enhance error tolerance in fusion-based quantum computing. By 
adaptively choosing bias during operations, it triples the loss tolerance.
- **Link**: [Read the paper](https://arxiv.org/pdf/2303.16122.pdf)

3. **Fault Tolerant Non-Clifford State Preparation for Arbitrary Rotations**  
- **Published Date**: March 30, 2023  
- **Authors**: Hyeongrak Choi, Frederic T. Chong, Dirk Englund, Yong Ding  
- **Summary**: This paper proposes a post-selection-based algorithm for 
efficiently preparing resource states for gate teleportation, achieving fault
tolerance with reduced resource overheads for non-Clifford rotations.
- **Link**: [Read the paper](https://export.arxiv.org/pdf/2303.17380v1.pdf)

4. **Measurement-free Fault-tolerant Logical Zero-state Encoding**  
- **Published Date**: June 2, 2023  
- **Authors**: Hayato Goto, Yinghao Ho, Taro Kanao  
- **Summary**: This work presents an efficient encoding method for the 
nine-qubit surface code that requires no measurement and can operate on a 
one-dimensional qubit array, demonstrating its fault tolerance.
- **Link**: [Read the paper](https://export.arxiv.org/pdf/2303.17211v2.pdf)

5. **High-threshold and Low-overhead Fault-tolerant Quantum Memory**  
- **Published Date**: March 27, 2024  
- **Author**: Theodore J. Yoder  
- **Summary**: This research discusses high-rate LDPC codes for quantum error
correction, presenting codes that require fewer physical qubits compared to
traditional surface codes while achieving similar error thresholds.
- **Link**: [Read paper](https://www.nature.com/articles/s41586-024-07107-7)

These studies reflect ongoing advances in quantum error correction, focusing 
on improving efficiency, fault tolerance, and minimizing resource overheads.
===============================================================================
"""

search_alibaba_tongxiao_response = SearchToolkit().search_alibaba_tongxiao(
    query="Alibaba's chip investment for 2025", time_range="OneMonth"
)
print(search_alibaba_tongxiao_response)
# ruff: noqa: RUF001
"""
===============================================================================
{'request_id': '78a77a7e004dd97bc18bd907b90d152b', 'results': [
{'result_id': 1, 'title': 'Investor Relations', 'snippet':
 'Stock Information Alibaba Group(BABA)-NYSE 112.280 1.690（-1.483%） 
 2025-04-15T20:01 EDT Prices shown in USD The data service is provided
   by Alibaba Cloud,with a delay of at least 15 minutes. Alibaba 
   Group(9988)-H...', 'url': 'https://www.alibabagroup.com/
   en-US/investor-relations', 'hostname': 'www.alibabagroup.com', 
   'summary': 'February 20, 2025\nAlibaba Group Will Announce December
   Quarter 2024 Results on February 20, 2025April 2, 2025\nAlibaba Group 
   Announces December Quarter 2024 Results\nFebruary 20, 2025Stock 
   Information\nAlibaba Group (BABA) - NYSE\n$\n112.280\n-$1.690（-1.483%
   2025-04-15T20:01 EDTAlibaba Group (9988) - HKEX\nHK$\n104.400\n-HK$5.500
   （-5.005%）\n2025-04-16T12:00 HKT\nPrices shown in HKD', 
   'score': 0.33736322991609163, 'publish_time': 1744646400000},
{'result_id': 2, 'title': 'technode'.....}
]}
===============================================================================
"""
# Example using metaso response
metaso_response = SearchToolkit().search_metaso(
    query="What is CAMEL-AI?",
    scope="webpage",
    page=1,
)

print(metaso_response)
"""
===============================================================================
{'credits': 10, 'searchParameters': {'q': 'What is CAMEL-AI?', 'scope': 'webpage',
 'page': 1, 'includeSummary': False, 'includeRawContent': False, 'conciseSnippet':
  False, 'format': 'chat_completions'}, 'webpages': [{'title': '使用CAMEL框架和Qwen
  模型自动进行数据获取及报告与知识 ...', 'link': 'https://developer.aliyun.com/articl
  e/1647631', 'score': 'high', 'snippet': '**关于CAMEL AI**\n* * *\n**"Finding the
   Scaling Law of Agents"**\nCAMEL AI (https://www.camel-ai.org) 是一个致力于构建基
   于大语言模型(LLMs)的多智能体系统的开源平台,旨在推动人工智能的发展。就像AI领域的“沙
   漠之舟”,CAMEL不仅在信息的广袤领域里稳步前行,更为实现AGI探索出一条前沿之路。CAMEL框架
   是最早基于ChatGPT的autonomous agents的知名项目,已被NeurlPS 2023录用。', 'position'
   : 1, 'authors': ['阿里云开发者社区'], 'date': '2024年12月31日'}, {'title':
   'CAMEL-AI团队参与发表Nature子刊啦!聚焦LLM如何重塑 ...', 'link': 'https://cloud.
   tencent.com/developer/article/2475624', 'score': 'high', 'snippet': 'Finding
   the Scaling Law of Agents"\nCAMEL AI (https://www.camel-ai.org) 是一个致力于构建
   基于大语言模型)LLMs)的多智能体系统的开源平台，旨在推动人工智能的发展。\n就像AI领域的
   “沙漠之舟”,CAMEL不仅在信息的广袤领域里稳步前行,更为实现AGI探索出一条前沿之路。\n
   CAMEL框架是最早基于ChatGPT的autonomous agents的知名项目,已被NeurlPS 2023录用。\n
   CAMEL AI框架设计上极具灵活性与模块化,包含多种智能体实现、专业领域提示示例以及AI数据探
   索功能等模块，适应各种高效决策与复杂数据处理需求。\n通过协作运作的智能体队列,CAMEL AI
   不仅在金融、零售、医疗等领域展示出强大的适用性和创新性，还大大提升了自适应能力......
   'position': 9, 'authors': ['KubeNine'], 'date': '2025年04月15日'}, {'title': '
   RAG应用的评估-CSDN博客', 'link': 'https://blog.csdn.net/weixin_44245188/article/
   details/148157069', 'score': 'high', 'snippet': "Query: 什么是CAMEL AI?\n
   Expected Answers: ['CAMEL AI 是一个开源的、社区驱动的AI框架。']\nRetrieved
   Results: ['CAMEL AI 介绍\\n\\nCAMEL AI 是一个开源的、社区驱动的AI框架,旨在简化AI应
   用的开发和部署。该框架提供了多种功能模块，包括数据加载、特征工程、模型训练和部署等。']
   \nPrecision: 1.0000\nRecall: 1.0000\nF1 Score: 1.0000\nAverage
 Similarity: 0.9584", 'position': 10, 'date': '2025年05月23日'}], 'total': 38}
===============================================================================
"""  # noqa: E501
