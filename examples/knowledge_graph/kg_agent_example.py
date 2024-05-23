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
from camel.agents import KnowledgeGraphAgent
from camel.loaders import UnstructuredIO

# Set instance
uio = UnstructuredIO()
kg_agent = KnowledgeGraphAgent()

# Set example text input
text_example = """CAMEL-AI.org is an open-source community dedicated to the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we provide, implement, and support various types of agents, tasks, prompts, models, datasets, and simulated environments.
"""

# Create an element from given text
element_example = uio.create_element_from_text(text=text_example)

# Let KnowledgeGraph Agent extract node and relationship information
ans = kg_agent.run(element_example)

# Get output
print(ans)
"""
===============================================================================
Nodes:

Node(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'})
Node(id='community', type='Concept', properties={'agent_generated'})
Node(id='study', type='Concept', properties={'agent_generated'})
Node(id='autonomous agents', type='Concept', properties={'agent_generated'})
Node(id='communicative agents', type='Concept', properties={'agent_generated'})
Node(id='insights', type='Concept', properties={'agent_generated'})
Node(id='behaviors', type='Concept', properties={'agent_generated'})
Node(id='capabilities', type='Concept', properties={'agent_generated'})
Node(id='risks', type='Concept', properties={'agent_generated'})
Node(id='research', type='Concept', properties={'agent_generated'})
Node(id='field', type='Concept', properties={'agent_generated'})
Node(id='agents', type='Concept', properties={'agent_generated'})
Node(id='tasks', type='Concept', properties={'agent_generated'})
Node(id='prompts', type='Concept', properties={'agent_generated'})
Node(id='models', type='Concept', properties={'agent_generated'})
Node(id='datasets', type='Concept', properties={'agent_generated'})
Node(id='simulated environments', type='Concept', properties={'agent_generated'})

Relationships:

Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node(id='community', type='Concept'), type='DedicatedTo', properties={'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node(id='study', type='Concept'), type='DedicatedTo', properties={'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node(id='autonomous agents', type='Concept'), type='DedicatedTo', properties={'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node(id='communicative agents', type='Concept'), type='DedicatedTo', properties={'agent_generated'})
Relationship(subj=Node(id='study', type='Concept'), obj=Node(id='insights', type='Concept'), type='Offers', properties={'agent_generated'})
Relationship(subj=Node(id='study', type='Concept'), obj=Node(id='behaviors', type='Concept'), type='Offers', properties={'agent_generated'})
Relationship(subj=Node(id='study', type='Concept'), obj=Node(id='capabilities', type='Concept'), type='Offers', properties={'agent_generated'})
Relationship(subj=Node(id='study', type='Concept'), obj=Node(id='risks', type='Concept'), type='Offers', properties={'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node(id='research', type='Concept'), type='Facilitate', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='field', type='Concept'), type='In', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='agents', type='Concept'), type='In', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='tasks', type='Concept'), type='In', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='prompts', type='Concept'), type='In', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='models', type='Concept'), type='In', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='datasets', type='Concept'), type='In', properties={'agent_generated'})
Relationship(subj=Node(id='research', type='Concept'), obj=Node(id='simulated environments', type='Concept'), type='In', properties={'agent_generated'})
===============================================================================
"""
