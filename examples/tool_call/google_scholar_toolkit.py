# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import GoogleScholarToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name='Tools calling opertor', content='You are a helpful assistant'
)

# Set model config
tools = GoogleScholarToolkit(
    author_identifier="https://scholar.google.com/citations?user=J9K-D0sAAAAJ"
).get_tools()
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Define a user message
usr_msg = BaseMessage.make_user_message(
    role_name='CAMEL User',
    content='get the detailed information of this author',
)

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[FunctionCallingRecord(func_name='get_author_detailed_info', args={}, result=
{'container_type': 'Author', 'filled': ['basics', 'indices', 'counts', 
'coauthors', 'publications', 'public_access'], 'scholar_id': 'J9K-D0sAAAAJ', 
'source': <AuthorSource.AUTHOR_PROFILE_PAGE: 'AUTHOR_PROFILE_PAGE'>, 'name': 
'Guohao Li', 'url_picture': 'https://scholar.googleusercontent.com/citations?
view_op=view_photo&user=J9K-D0sAAAAJ&citpid=6', 'affiliation': 'University of 
Oxford, CAMEL-AI.org', 'organization': 273144080909810983, 'interests': 
['Autonomous Agents', 'Graph Neural Networks', 'Computer Vision', 'Embodied 
AI'], 'email_domain': '@robots.ox.ac.uk', 'homepage': 'http://ghli.org/', 
'citedby': 3780, 'citedby5y': 3776, 'hindex': 14, 'hindex5y': 14, 
'i10index': ..
===============================================================================
"""

# Define a user message
usr_msg = BaseMessage.make_user_message(
    role_name='CAMEL User', content='get the publications of this author'
)

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[FunctionCallingRecord(func_name='get_author_publications', args={}, result=
['DeepGCNs: Can GCNs Go as Deep as CNNs?', 'DeeperGCN: Training Deeper GCNs 
with Generalized Aggregation Functions', 'Camel: Communicative agents for" 
mind" exploration of large language model society', 'Training Graph Neural 
Networks with 1000 Layers', 'SGAS: Sequential Greedy Architecture Search', 
'PU-GCN: Point Cloud Upsampling using Graph Convolutional Networks', 'Flag: 
Adversarial data augmentation for graph neural networks', 'ASSANet: An 
Anisotropic Separable Set Abstraction for Efficient Point Cloud Representation 
Learning', 'Mindstorms in natural language-based societies of mind', 'OIL: 
Observational Imitation Learning', 'Diffusion-based scene graph to image 
generation with masked contrastive pre-training', 'Can Large Language Model 
Agents Simulate Human Trust Behaviors?', 'How To Not Train Your Dragon: 
Training-free Embodied Object Goal Navigation with Semantic Frontiers', 'Brave 
the wind and the waves: Discovering robust and generalizable graph lottery 
tickets', 'The snowflake hypothesis: Training deep GNN with one node one 
receptive field', 'Learning a controller fusion network by online trajectory 
filtering for vision-based uav racing', 'LC-NAS: Latency constrained neural 
architecture search for point cloud networks', 'When NAS Meets Trees: An 
Efficient Algorithm for Neural Architecture Search', 'Leveraging 2D molecular 
graph pretraining for improved 3D conformer generation with graph neural 
networks', 'Learning scene flow in 3d point clouds with noisy pseudo labels', 
'DeepGCNs: Making GCNs Go as Deep as CNNs', 'The heterophilic snowflake 
hypothesis: Training and empowering gnns for heterophilic graphs', 'Technology 
for memory-efficient and parameter-efficient graph neural networks', 
'Knowledge-aware Global Reasoning for Situation Recognition', 'CRAB: 
Cross-environment Agent Benchmark for Multimodal Language Model Agents', 
'UnrealNAS: Can We Search Neural Architectures with Unreal Data?', 'The 
Snowflake Hypothesis: Training and Powering GNN with One Node One Receptive 
Field', 'All Nodes are created Not Equal: Node-Specific Layer Aggregation and 
Filtration for GNN', 'Towards Structured Intelligence with Deep Graph Neural 
Networks', 'DEEPERBIGGERBETTER FOR OGB-LSC AT KDD CUP 2021'])]
===============================================================================
"""

# ruff: noqa: E501
# Define a user message
usr_msg = BaseMessage.make_user_message(
    role_name='CAMEL User',
    content='get the detailed information for publication with title: `Camel: Communicative agents for" mind" exploration of large language model society`',
)

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[FunctionCallingRecord(func_name='get_publication_by_title', args=
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
“cognitive” processes. To address the challenges of achieving autonomous 
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
