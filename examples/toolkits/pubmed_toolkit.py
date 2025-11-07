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
from camel.toolkits import PubMedToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize PubMed toolkit and get tools
tools = PubMedToolkit().get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create chat agent
system_msg = (
    "You are a research assistant specialized in medical literature. "
    "Help researchers find and analyze scientific papers from PubMed."
)
camel_agent = ChatAgent(
    system_message=system_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Example 1: Search for recent papers about mRNA vaccine technology
print("\nExample 1: Search for recent papers about mRNA vaccine technology")
print("=" * 80)

usr_msg = (
    "Find recent review papers about mRNA vaccine technology published "
    "in 2024, with a focus on therapeutic applications and clinical trials. "
    "Limit to 3 papers."
)

response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:2000])

"""
===============================================================================
ToolCallingRecord(
    tool_name='search_papers',
    args={
        'query': 'mRNA vaccine tech therapeutic applications trials',
        'max_results': 10,
        'sort': 'date',
        'date_range': {'from': '2024/01/01', 'to': '2024/12/31'},
        'publication_type': ['Review'],
    },
    result=[
        {
            'id': '39601789',
            'title': 'Example Title',
            'authors': 'First Author, Second Author',
            'journal': 'Example Journal',
            'pub_date': '2025 Jan 6',
            'abstract': 'Abstract of the paper',
===============================================================================
"""


# Example 2: Get detailed information about a specific paper
print("\nExample 2: Get detailed paper information")
print("=" * 80)

usr_msg = (
    "Get detailed information about PubMed ID 39601789 "
    "(a key paper about mRNA vaccine technology)."
)
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:2000])

"""
===============================================================================
[ToolCallingRecord(
    tool_name='get_paper_details',
    args={'paper_id': 37840631, 'include_references': True},
    result={
        'id': '37840631',
        'title': 'Chinese guideline for lipid management (2023):
                  a new guideline rich in domestic elements for 
                  controlling dyslipidemia.',
        'authors': 'Li JJ',
        'journal': 'J Geriatr Cardiol',
        'pub_date': '2023 Sep 28',
        'abstract': '1. J Geriatr Cardiol. 
                     2023 Sep 28;20(9):618-620. 
                     doi: 10.26599/1671-5411.2023.09.007.
                     Chinese guideline for lipid management (2023):
                     a new guideline rich in domestic elements for 
                     controlling dyslipidemia.Li JJ(1).\Author information:
                     (1)Division of Cardio-Metabolic Center,
                     State Key Laboratory of Cardiovascular 
                     Disease, Fu Wai Hospital, National Center 
                     for Cardiovascular Disease, Chinese Academy
                     of Medical Sciences, Peking Union Medical College,
                     Beijing, China.DOI: 10.26599/1671-5411.2023.09.007
                     PMCID: PMC10568543\nPMID: 37840631',
        'doi': 'doi: 10.26599/1671-5411.2023.09.007',
        'keywords': [],
        'mesh_terms': [],
        'publication_types': ['Journal Article'],
        'references': ['35729555', '34734202', '34404993', 
                       '31172370', '30586774', '30526649', 
                       '29434622', '20350253']
    },
    tool_call_id='call_k8s7oFcRvDBKuEKvk48uoWXZ'
)]
===============================================================================
"""

# Example 3: Find related papers and citation metrics
print("\nExample 3: Find related papers and citation metrics")
print("=" * 80)

usr_msg = (
    "Find papers related to PubMed ID 39601789 (limit to 3 papers) and "
    "show its citation count."
)
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:2000])

"""
===============================================================================
[ToolCallingRecord(
    tool_name='get_related_papers',
    args={'paper_id': 37840631, 'max_results': 5},
    result=[
        {'id': '37840631',
         'title': 'Chinese guideline for lipid management (2023):
                   a new guideline rich in domestic elements for 
                   controlling dyslipidemia.',
         'authors': 'Li JJ',
         'journal': 'J Geriatr Cardiol',
         'pub_date': '2023 Sep 28',
         'abstract': (
             '1. J Geriatr Cardiol. 2023 Sep 28;20(9):618-620. doi: '
             '10.26599/1671-5411.2023.09.007.'
             'Chinese guideline for lipid management (2023): a new guideline'
             'rich in domestic elements for controlling dyslipidemia.'
             'Li JJ(1).Author information:(1)Division of Cardio-Metabolic '
             'Center, State Key Laboratory of Cardiovascular Disease, Fu Wai '
             'Hospital, National Center for Cardiovascular Disease, Chinese '
             'Academy of Medical Sciences, Peking Union Medical College, '
             'Beijing, China.DOI: 10.26599/1671-5411.2023.09.007'
             'PMCID: PMC10568543  PMID: 37840631'
         ),
         'doi': 'doi: 10.26599/1671-5411.2023.09.007',
         'keywords': [],
         'mesh_terms': [],
         'publication_types': ['Journal Article'],
         'references': None},
        {'id': '22801311',
         'title': (
             '[Short-term impact of modified blood-lipid reports on physicians'
             'lipid lowering drug prescribing behavior and knowledge '
             'improvement on dyslipidemia].'
         ),
         'authors': 'Li JH, Jiang H, Sun XH, Li CC, Ke YN, Yan SK, Wu YF',
         'journal': 'Zhonghua Xin Xue Guan Bing Za Zhi',
         'pub_date': '2012 Apr',
         'abstract': (
             '1. Zhonghua Xin Xue Guan Bing Za Zhi. 2012 Apr;40(4):318-22.'
             '[Short-term impact modified blood-lipid reports on physicians'
             'lipid lowering drug prescribing behavior and knowledge '
             'improvement on dyslipidemia].Article in Chinese]'
             'Li JH(1), Jiang H, Sun XH, Li CC, Ke YN, Yan SK, Wu YF.'
             'Author information:(1)Department of Cardiology, China-Japan'
===============================================================================
"""

# Example 4: Advanced search with multiple filters
print("\nExample 4: Advanced search with multiple filters")
print("=" * 80)

usr_msg = (
    "Find clinical trial papers about mRNA-based cancer vaccines published "
    "between 2023/01/01 and 2024/03/01, focusing on phase III trials. "
    "Limit to 3 papers."
)
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:2000])

"""
===============================================================================
[ToolCallingRecord(
    tool_name='search_papers',
    args={
        'query': 'mRNA cancer vaccine phase III clinical trial',
        'max_results': 10,
        'sort': 'date',
        'date_range': {'from': '2023/01/01', 'to': '2024/03/01'},
        'publication_type': ['Clinical Trial']
    },
    result=[
        {
            'id': '37820782',
            'title': 'Stochastic interventional approach to assessing immune '
                      'correlates of protection: Application to the COVE '
                      'RNA-1273 vaccine trial.',
            'authors': (
                'Hejazi NS, Shen X, Carpp LN, Benkeser D, Follmann D, 
                Janes HE, Baden LR, El Sahly HM, Deng W, Zhou H, 
                Leav B, Montefiori DC, 'Gilbert PB'
            ),
            'journal': 'Int J Infect Dis',
            'pub_date': '2023 Dec',
            'abstract': Abstract of the paper
===============================================================================
"""

# Example 5: Get abstract and analyze citations
print("\nExample 5: Get abstract and analyze citations")
print("=" * 80)

usr_msg = (
    "Get the abstract of PubMed ID 39601789 and find out how many times "
    "it has been cited."
)
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:2000])

"""
===============================================================================
[
    ToolCallingRecord(
        tool_name='get_abstract',
        args={'paper_id': 37840631},
        result='''
            1. J Geriatr Cardiol. 2023 Sep 28;20(9):618-620. doi: 
            10.26599/1671-5411.2023.09.007.
            
            Chinese guideline for lipid management (2023):a new guideline 
            rich in domestic elements for controlling dyslipidemia.
            
            Li JJ(1).
            
            Author information:
            (1)Division of Cardio-Metabolic Center, State Key Laboratory
            of Cardiovascular Disease, Fu Wai Hospital, National Center 
            for Cardiovascular Disease, Chinese Academy of Medical Sciences,
            Peking Union Medical College, Beijing, China.
            
            DOI: 10.26599/1671-5411.2023.09.007
            PMCID: PMC10568543
            PMID: 37840631
        ''',
        tool_call_id='call_AFG6jLkdvWidaVGrj9UblTci'
    ),
    ToolCallingRecord(
        tool_name='get_citation_count',
        args={'paper_id': 37840631},
        result=0,
        tool_call_id='call_ZM3p59gtYmeR9DPdONNHV4Qw'
    )
]
===============================================================================
"""
