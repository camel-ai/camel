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
from camel.toolkits import SemanticScholarToolkit
from camel.types import ModelPlatformType, ModelType

# Define the model, here in this case we use gpt-4o
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)


sys_msg = "You are a helpful assistant"

# Initialize a toolkit
toolkit = SemanticScholarToolkit()
# Get list of tools
tools = toolkit.get_tools()

# Initialize a ChatAgent with your custom tools
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Description of the added tools
usr_msg = "Describe the tools you've added"

response = camel_agent.step(usr_msg)
print(response.msgs[0].content)

'''
================================================================
1. **fetch_paper_data_title**: This tool fetches a single paper
 based on its title. You can specify which fields to include in
 the response, such as the abstract, authors, year, citation
 count, and more.

2. **fetch_paper_data_id**: Similar to the previous tool,
 this one retrieves a single paper but uses a paper ID instead
 of the title. It also allows for specifying the fields to
 include in the response.

3. **fetch_bulk_paper_data**: This tool allows you to fetch
 multiple papers at once based on a query that can include
 various operators (like AND, OR, NOT). You can filter by
 year and specify which fields to return.

4. **fetch_recommended_papers**: This tool provides
 recommendations for papers based on a list of positively
 and negatively correlated paper IDs. You can specify the
 fields to include in the response and limit the number
 of papers returned.

5. **fetch_author_data**: This tool retrieves information
 about authors based on their IDs. You can specify which
 fields to include in the response, such as the author's name,
 URL, paper count, h-index, and their papers.

These tools can be used individually or in combination to
 gather comprehensive information about academic literature
 and authors.
================================================================
'''

# Search a paper through its id
usr_msg = """search the paper 'Construction of the Literature
    Graph in Semantic Scholar' for me including its paperid"""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_paper_data_title', 
args={'paperTitle': 'Construction of the Literature Graph in
Semantic Scholar', 'fields': 'title,abstract,authors,year,
citationCount,paperId'}, result={'total': 1, 'offset': 0,
'data': [{'paperId': '649def34f8be52c8b66281af98ae884c09aef38b',
'title': 'Construction of the Literature Graph in Semantic
 Scholar', 'abstract': 'We describe a deployed scalable system
for organizing published scientific literature into a 
heterogeneous graph to facilitate algorithmic manipulation and 
discovery. The resulting literature graph consists of more than
 280M nodes, representing papers, authors, entities and various
 interactions between them (e.g., authorships, citations, 
 entity mentions). We reduce literature graph construction into
 familiar NLP tasks (e.g., entity extraction and linking),
 point out research challenges due to differences from standard
 formulations of these tasks, and report empirical results for
 each task. The methods describe
================================================================
'''

# Search a paper through its title
usr_msg = """search the paper with paper id of 
    '649def34f8be52c8b66281af98ae884c09aef38b' for me"""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_paper_data_id', args=
{'paperID': '649def34f8be52c8b66281af98ae884c09aef38b', 
'fields': 'title,abstract,authors,year,citationCount,
publicationTypes,publicationDate,openAccessPdf'}, 
result={'paperId': '649def34f8be52c8b66281af98ae884c09aef38b',
'title': 'Construction of the Literature Graph in Semantic
 Scholar', 'abstract': 'We describe a deployed scalable system
 for organizing published scientific literature into a
 heterogeneous graph to facilitate algorithmic manipulation
 and discovery. The resulting literature graph consists of 
 more than 280M nodes, representing papers, authors, entities
 and various interactions between them (e.g., authorships,
 citations, entity mentions). We reduce literature graph
 construction into familiar NLP tasks (e.g., entity extraction
 and linking), point out research challenges due to differences
 from standard formulations of these tasks, and report
 empirical results for each task. The methods described
 in this paper ar
================================================================
'''

# Search papers through related topic
usr_msg = """search 3 papers with topic related to
    'generative ai' from 2024 for me"""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_bulk_paper_data', 
args={'query': 'generative ai', 'year': '2024-', 'fields':
'title,url,publicationTypes,publicationDate,openAccessPdf'},
result={'total': 9849, 'token': 'PCOA3RZZB2ADADAEYCX2BLJJRDEGL
PUCFA3I5XJAKEAB3YXPGDOTY2GU3WHI4ZMALUMAPUDPHP724CEUVEFKTYRZY5K
LUU53Y5MWWEINIKYZZRC3YT3H4AF7CTSQ', 'data': [{'paperId': 
'0008cd09c0449451b9e6e6de35c29009f0883cd9', 'url': 'https://www
.semanticscholar.org/paper/0008cd09c0449451b9e6e6de35c29009
f0883cd9', 'title': 'A Chitchat on Using ChatGPT for Cheating',
 'openAccessPdf': {'url': 'https://doi.org/10.34074/proc.240106'
 , 'status': 'BRONZE'}, 'publicationTypes': ['Conference'], 
 'publicationDate': '2024-07-24'}, {'paperId': '0013aecf813400
 174158e4f012918c5408f90962', 'url': 'https://www.semanticsc
 holar.org/paper/0013aecf813400174158e4f012918c5408f90962', 
 'title': 'Can novice teachers detect AI-generated texts in EFL
 writing?', 'openAccessPdf': None, 'publicationTypes':
 ['JournalArticle'], 'publicationDate'
================================================================
'''

# Search papers through related topic and operator
usr_msg = """search 2 papers with topic related to
    'ai and bio' from 2024 for me"""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_bulk_paper_data', 
args={'query': 'ai and bio', 'year': '2024-', 'fields': 'title,
url,publicationTypes,publicationDate,openAccessPdf'}, result=
{'total': 207, 'token': None, 'data': [{'paperId': '00c8477a9c
c28b85e4f6da13d2a889c94a955291', 'url': 'https://www.semantics
cholar.org/paper/00c8477a9cc28b85e4f6da13d2a889c94a955291', 
'title': 'Explaining Enterprise Knowledge Graphs with Large
 Language Models and Ontological Reasoning', 'openAccessPdf': 
 None, 'publicationTypes': ['JournalArticle'], 'publicationDate
 ': None}, {'paperId': '01726fbfc8ee716c82b9c4cd70696906d3a4
 46d0', 'url': 'https://www.semanticscholar.org/paper/01726fbfc
 8ee716c82b9c4cd70696906d3a446d0', 'title': 'Study Research 
 Protocol for Phenome India-CSIR Health Cohort Knowledgebase
 (PI-CHeCK): A Prospective multi-modal follow-up study on a 
 nationwide employee cohort.', 'openAccessPdf': {'url': 
 'https://www.medrxiv.org/content/medrxiv/early/2024/10/19/2024
 .10.17.24315252.full.pdf', 'status'
================================================================
'''

# Recommend papers through positive and negative paper id
usr_msg = """recommend 2 papers with positive paper id
    of "02138d6d094d1e7511c157f0b1a3dd4e5b20ebee",
    "018f58247a20ec6b3256fd3119f57980a6f37748" and negative
    paper id of "0045ad0c1e14a4d1f4b011c92eb36b8df63d65bc"
    for me"""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_recommended_papers',
args={'positive_paper_ids': ['02138d6d094d1e7511c157f0b1a3dd4e
5b20ebee', '018f58247a20ec6b3256fd3119f57980a6f37748'], 'negati
ve_paper_ids': ['0045ad0c1e14a4d1f4b011c92eb36b8df63d65bc'], 
'fields': 'title,url,citationCount,authors,publicationTypes,
publicationDate,openAccessPdf', 'limit': 20, 'save_to_file': F
alse}, result={'recommendedPapers': [{'paperId': '9cb202a72171
dc954f8180b42e08da7ab31e16a1', 'url': 'https://www.semanticsc
holar.org/paper/9cb202a72171dc954f8180b42e08da7ab31e16a1', 'tit
le': 'Embrace, Don't Avoid: Reimagining Higher Education with
 Generative Artificial Intelligence', 'citationCount': 0, 'op
 enAccessPdf': {'url': 'https://heca-analitika.com/jeml/arti
 cle/download/233/157', 'status': 'HYBRID'}, 'publicationT
 ypes': ['JournalArticle'], 'publicationDate': '2024-11-2
 8', 'authors': [{'authorId': '1659371967', 'name': 'T. R. N
 oviandy'}, {'authorId': '1657989613', 'name': 'A. Maulan
 a'}, {'authorId': '146805414', 'name
================================================================
'''

# Recommend papers and save the result in a file
usr_msg = """search the authors of author ids of "2281351310",
    "2281342663","2300302076","2300141520" for me"""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_recommended_papers', 
args={'positive_paper_ids': ['02138d6d094d1e7511c157f0b1a3dd4e5
b20ebee', '018f58247a20ec6b3256fd3119f57980a6f37748'], 'negativ
e_paper_ids': ['0045ad0c1e14a4d1f4b011c92eb36b8df63d65bc'],
 'fields': 'title,url,citationCount,authors,publicationTypes,
 publicationDate,openAccessPdf', 'limit': 20, 'save_to_file': T
 rue}, result={'recommendedPapers': [{'paperId': '9cb202a7217
 1dc954f8180b42e08da7ab31e16a1', 'url': 'https://www.semantics
 cholar.org/paper/9cb202a72171dc954f8180b42e08da7ab31e16a1', 
 'title': 'Embrace, Don't Avoid: Reimagining Higher Education
 with Generative Artificial Intelligence', 'citationCount':
 0, 'openAccessPdf': {'url': 'https://heca-analitika.com/jeml
 /article/download/233/157', 'status': 'HYBRID'}, 'publication
 Types': ['JournalArticle'], 'publicationDate': '2024-11-28',
 'authors': [{'authorId': '1659371967', 'name': 'T. R. Novia
 ndy'}, {'authorId': '1657989613', 'name': 'A. Maulana'}, 
 {'authorId': '146805414', 'name'
================================================================
'''

# Search author information through author id
usr_msg = """recommend 2 papers with positive paper id
    of "02138d6d094d1e7511c157f0b1a3dd4e5b20ebee", "018f5
    8247a20ec6b3256fd3119f57980a6f37748" and negative paper
    id of "0045ad0c1e14a4d1f4b011c92eb36b8df63d65bc" for me,
    and please save the result in a file."""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_recommended_papers', 
args={'positive_paper_ids': ['02138d6d094d1e7511c157f0b1a3dd4e5
b20ebee', '018f58247a20ec6b3256fd3119f57980a6f37748'], 'negat
ive_paper_ids': ['0045ad0c1e14a4d1f4b011c92eb36b8df63d65bc'],
 'fields': 'title,url,citationCount,authors,publicationTypes
 ,publicationDate,openAccessPdf', 'limit': 20, 'save_to_file
 ': True}, result={'recommendedPapers': [{'paperId': '9cb20
 2a72171dc954f8180b42e08da7ab31e16a1', 'url': 'https://www.se
 manticscholar.org/paper/9cb202a72171dc954f8180b42e08da7ab31e
 16a1', 'title': 'Embrace, Don't Avoid: Reimagining Higher 
 Education with Generative Artificial Intelligence', 'citat
 ionCount': 0, 'openAccessPdf': {'url': 'https://heca-anali
 tika.com/jeml/article/download/233/157', 'status': 'HYBR
 ID'}, 'publicationTypes': ['JournalArticle'], 'publicatio
 nDate': '2024-11-28', 'authors': [{'authorId': '165937196
 7', 'name': 'T. R. Noviandy'}, {'authorId': '1657989613',
 'name': 'A. Maulana'}, {'authorId': '146805414', 'name'
================================================================
'''

# Search author information and save the result in a file
usr_msg = """search the authors of author ids of "2281351310"
    ,"2281342663","2300302076","2300141520" for me, and please
    save the record in a file."""
camel_agent.reset()
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])

'''
================================================================
[FunctionCallingRecord(func_name='fetch_author_data', args=
{'ids': ['2281351310', '2281342663', '2300302076', '230014152
0'], 'fields': 'name,url,paperCount,hIndex,papers', 'save_to_
file': True}, result=[{'authorId': '2281351310', 'url': 'ht
tps://www.semanticscholar.org/author/2281351310', 'name': 'Tho
mas K. F. Chiu', 'paperCount': 3, 'hIndex': 1, 'papers': [{'p
aperId': '218b2e3d3418edff705336a6e0c7f2125be7c562', 'title': N
one}, {'paperId': '630642b7040a0c396967e4dab93cf73094fa4f8f
', 'title': None}, {'paperId': '833ff07d2d1be9be7b12e88487d5631
c141a2e95', 'title': None}]}, {'authorId': '2281342663', 'ur
l': 'https://www.semanticscholar.org/author/2281342663', 'nam
e': 'C. Chai', 'paperCount': 6, 'hIndex': 2, 'papers': [{'pape
rId': '0c70ca68c0239895b0d36abf7f11302cdcf01855', 'title': Non
e}, {'paperId': '218b2e3d3418edff705336a6e0c7f2125be7c562', 't
itle': None}, {'paperId': '7ce699e1cfb81cecf298df6be8eaac8f50
2e0fcc', 'title': None}, {'paperId': '4521b51a8465e69d20a3ae4
b770cf164a180f67b', 'ti
================================================================
'''
