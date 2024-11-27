# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from camel.agents import KnowledgeGraphAgent
from camel.loaders import UnstructuredIO

# Set instance
uio = UnstructuredIO()
kg_agent = KnowledgeGraphAgent()

# Set example text input
text_example = """CAMEL-AI.org is an open-source community dedicated to the 
study of autonomous and communicative agents. 
"""

# Create an element from given text
element_example = uio.create_element_from_text(text=text_example)

# Let KnowledgeGraph Agent extract node and relationship information
ans_str = kg_agent.run(element_example, parse_graph_elements=False)
ans_GraphElement = kg_agent.run(element_example, parse_graph_elements=True)

# Get str output
print(ans_str)

# Get GraphElement output
print(ans_GraphElement)

"""
===============================================================================
Nodes:

Node(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'})
Node(id='community', type='Concept', properties={'agent_generated'})
Node(id='study', type='Concept', properties={'agent_generated'})
Node(id='autonomous agents', type='Concept', properties={'agent_generated'})
Node(id='communicative agents', type='Concept', properties={'agent_generated'})

Relationships:

Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='community', type='Concept'), type='FocusOn', properties=
{'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='study', type='Concept'), type='FocusOn', properties={'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='autonomous agents', type='Concept'), type='FocusOn', properties=
{'agent_generated'})
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), obj=Node
(id='communicative agents', type='Concept'), type='FocusOn', properties=
{'agent_generated'})
===============================================================================
"""

"""
===============================================================================
GraphElement(nodes=[Node(id='CAMEL-AI.org', type='Organization', properties=
{'agent_generated'}), Node(id='community', type='Concept', properties=
{'agent_generated'}), Node(id='study', type='Concept', properties=
{'agent_generated'}), Node(id='autonomous agents', type='Concept', properties=
{'agent_generated'}), Node(id='communicative agents', type='Concept', 
properties={'agent_generated'})], relationships=[Relationship(subj=Node
(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'}), 
obj=Node(id='community', type='Concept', properties={'agent_generated'}), 
type='FocusOn', properties={"'agent_generated'"}), Relationship(subj=Node
(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'}), 
obj=Node(id='study', type='Concept', properties={'agent_generated'}), 
type='FocusOn', properties={"'agent_generated'"}), Relationship(subj=Node
(id='CAMEL-AI.org', type='Organization', properties={'agent_generated'}), 
obj=Node(id='autonomous agents', type='Concept', properties=
{'agent_generated'}), type='FocusOn', properties={"'agent_generated'"}), 
Relationship(subj=Node(id='CAMEL-AI.org', type='Organization', properties=
{'agent_generated'}), obj=Node(id='communicative agents', type='Concept', 
properties={'agent_generated'}), type='FocusOn', properties=
{"'agent_generated'"})], source=<unstructured.documents.elements.Text object 
at 0x7fd050e7bd90>)
===============================================================================
"""
