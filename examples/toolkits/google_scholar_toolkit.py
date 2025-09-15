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
from camel.toolkits import GoogleScholarToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = "You are a helpful assistant"

# Set model config
tools = GoogleScholarToolkit(
    author_identifier="https://scholar.google.com/citations?user=JicYPdAAAAAJ&hl=en&oi=ao"
).get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Define a user message
usr_msg = "get the detailed information of this author"

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(func_name='get_author_detailed_info', args={}, result=
{'container_type': 'Author', 'filled': ['basics', 'indices', 'counts', 
'coauthors', 'publications', 'public_access'], 'scholar_id': 'JicYPdAAAAAJ', 
'source': <AuthorSource.AUTHOR_PROFILE_PAGE: 'AUTHOR_PROFILE_PAGE'>, 'name': 
'Geoffrey Hinton', 'url_picture': 'https://scholar.googleusercontent.com/
citations?view_op=view_photo&user=JicYPdAAAAAJ&citpid=2', 'affiliation': 
'Emeritus Prof. Computer Science, University of Toronto', 'organization': 
8515235176732148308, 'interests': ['machine learning', 'psychology', 
'artificial intelligence', 'cognitive science', 'computer science'], 
'email_domain': '@cs.toronto.edu', 'homepage': 'http://www.cs.toronto.edu/
~hinton', 'citedby': 853541, 'citedby5y': 560063, 'hindex': 186, 'hindex5y': 
137, 'i10index': 483, 'i10index5y': 368, 'cites_per_year': {1989: 2627, 1990: 
3589, 1991: 3766, 1992: 4091, 1993: 4573, 1994: 4499, 1995: 4090, 1996: 3935, 
1997: 3740, 1998: 3744, 1999: 3559, 2000: 3292, 2001: 3398, 2002: 3713, 2003: 
3670, 2004: 3393, 2005: 3813, 2006: 4168, 2007: 4558, 2008: 4349, 2009: 4784, 
2010: 5238, 2011: 5722, 2012: 6746, 2013: 9900, 2014: 12751, 2015: 18999, 
2016: 29932, 2017: 43675, 2018: 63544, 2019: 80800, 2020: 90523, 2021: 101735, 
2022: 104036, 2023: 106452, 2024: 76413}, 'coauthors': [{'container_type': 
'Author', 'filled': [], 'scholar_id': 'm1qAiOUAAAAJ', 'source': <AuthorSource.
CO_AUTHORS_LIST: 'CO_AUTHORS_LIST'>, 'name': 'Terrence Sejnowski', 
'affiliation': 'Francis Crick Professor, Salk Institute, Distinguished 
Professor, UC San Diego'}, {'container_type': 'Author', 'filled': [], 
'scholar_id': 'RnoIxUwAAAAJ', 'source': <AuthorSource.CO_AUTHORS_LIST: 
'CO_AUTHORS_LIST'>, 'name': 'Vinod Nair', 'affiliation': 'Research Scientist, 
DeepMind'}, {'container_type': 'Author', 'filled': [], 'scholar_id': 
'ghbWy-0AAAAJ', 'source': <AuthorSource.CO_AUTHORS_LIST: 'CO_AUTHORS_LIST'>, 
'name': 'George E. Dahl', 'affiliation': 'Google Inc.'}, {'container_
===============================================================================
"""

# Define a user message
usr_msg = "get the publications of this author"

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(func_name='get_author_publications', args={}, result=
['Imagenet classification with deep convolutional neural networks', 'Deep 
learning', 'Learning internal representations by error-propagation', 'Dropout: 
a simple way to prevent neural networks from overfitting', 'Visualizing data 
using t-SNE', 'Learning representations by back-propagating errors', 'Learning 
multiple layers of features from tiny images', 'Rectified linear units improve 
restricted boltzmann machines', 'Reducing the dimensionality of data with 
neural networks', 'A fast learning algorithm for deep belief nets', 
'Distilling the Knowledge in a Neural Network', 'A simple framework for 
contrastive learning of visual representations', 'Deep neural networks for 
acoustic modeling in speech recognition: The shared views of four research 
groups', 'Layer normalization', 'Speech recognition with deep recurrent neural 
networks', 'Improving neural networks by preventing co-adaptation of feature 
detectors', 'Lec
===============================================================================
"""

# ruff: noqa: E501
# Define a user message

usr_msg = """get the detailed information for publication with title: `Camel: Communicative agents for" mind" exploration of large language model society`"""

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[ToolCallingRecord(func_name='get_publication_by_title', args=
{'publication_title': 'Camel: Communicative agents for" mind" exploration of 
large language model society'}, result={'container_type': 'Publication', 
'source': <PublicationSource.AUTHOR_PUBLICATION_ENTRY: 
'AUTHOR_PUBLICATION_ENTRY'>, 'bib': {'title': 'Camel: Communicative agents 
for" mind" exploration of large language model society', 'pub_year': 2023, 
'citation': 'Advances in Neural Information Processing Systems 36, 2023', 
'author': 'Guohao Li and Hasan Hammoud and Hani Itani and Dmitrii Khizbullin 
and Bernard Ghanem', 'journal': 'Advances in Neural Information Processing 
Systems', 'volume': '36', 'abstract': 'The rapid advancement of chat-based 
language models has led to remarkable progress in complex task-solving. 
However, their success heavily relies on human input to guide the 
conversation, which can be challenging and time-consuming. This paper explores 
the potential of building scalable techniques to facilitate autonomous 
cooperation among communicative agents, and provides insight into their 
"cognitive" processes. To address the challenges of achieving autonomous 
cooperation, we propose a novel communicative agent framework named 
role-playing. Our approach involves using inception prompting to guide chat 
agents toward task completion while maintaining consistency with human 
intentions. We showcase how role-playing can be used to generate 
conversational data for studying the behaviors and capabilities of a society 
of agents, providing a valuable resource for investigating conversational 
language models. In particular, we conduct comprehensive studies on 
instruction-following cooperation in multi-agent settings. Our contributions 
include introducing a novel communicative agent framework, offering a scalable 
approach for studying the cooperative behaviors and capabilities of 
multi-agent systems, and open-sourcing our library to support research on 
communicative agents and beyond: https://github. com/camel-ai/camel.'}, 
'filled': True, 'author_pub_id': 'J9K-D0sAAAAJ:_Qo2XoVZTnwC', 'num_citations': 
364, 'citedby_url': '/scholar?hl=en&cites=3976259482297250805', 'cites_id': 
['3976259482297250805'], 'pub_url': 'https://proceedings.neurips.cc/
paper_files/paper/2023/hash/
a3621ee907def47c1b952ade25c67698-Abstract-Conference.html', 
'url_related_articles': '/scholar?oi=bibs&hl=en&q=related:9TMbme6CLjcJ:scholar.
google.com/', 'cites_per_year': {2023: 95, 2024: 269}})]
===============================================================================
"""

usr_msg = """get the full information for paper from link: `https://hal.science/hal-04206682/document`"""

# Get response information
response = camel_agent.step(usr_msg)
print((response.info['tool_calls'])[:1000])
"""
===============================================================================
[ToolCallingRecord(func_name='get_full_paper_content_by_link', args=
{'pdf_url': 'https://hal.science/hal-04206682/document'}, result='Deep 
learning\nYann Lecun, Yoshua Bengio, Geoffrey Hinton\n\nTo cite this 
version:\n\nYann Lecun, Yoshua Bengio, Geoffrey Hinton. Deep learning. Nature, 
2015, 521 (7553), pp.436-444.\n\uffff10.1038/nature14539\uffff. 
\uffffhal-04206682\uffff\n\nHAL Id: hal-04206682\n\nhttps://hal.science/
hal-04206682v1\n\nSubmitted on 14 Sep 2023\n\nHAL is a multi-disciplinary open 
access\narchive for the deposit and dissemination of sci-\nentific research 
documents, whether they are pub-\nlished or not. The documents may come 
from\nteaching and research institutions in France or\nabroad, or from public 
or private research centers.\n\nL'archive ouverte pluridisciplinaire HAL, 
est\ndestinée au dépôt et à la diffusion de documents\nscientifiques de niveau 
recherche, publiés ou non,\némanant des établissements d'enseignement et 
de\nrecherche français ou étrangers, des laboratoires\npublics ou privés.
\n\n\x0cDeep learning\n\nYann LeCun1,2, Yoshua Bengio3 & Geoffrey Hinton4,
5\n\n1Facebook AI Research, 770 Broadway, New York, New York 10003 USA\n\n2N..
===============================================================================
"""
