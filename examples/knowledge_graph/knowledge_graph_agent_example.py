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
from dotenv import load_dotenv

from camel.agents import KnowledgeGraphAgent
from camel.loaders import UnstructuredIO

load_dotenv()

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


custom_prompt = """
You are tasked with extracting nodes and relationships from given content and 
structures them into Node and Relationship objects. Here's the outline of what 
you needs to do:

Content Extraction:
You should be able to process input content and identify entities mentioned 
within it.
Entities can be any noun phrases or concepts that represent distinct entities 
in the context of the given content.

Node Extraction:
For each identified entity, you should create a Node object.
Each Node object should have a unique identifier (id) and a type (type).
Additional properties associated with the node can also be extracted and 
stored.

Relationship Extraction:
You should identify relationships between entities mentioned in the content.
For each relationship, create a Relationship object.
A Relationship object should have a subject (subj) and an object (obj) which 
are Node objects representing the entities involved in the relationship.
Each relationship should also have a type (type), and additional properties if 
applicable.
**New Requirement:** 
Each relationship must have a timestamp representing the time the relationship 
was established or mentioned.

Output Formatting:
The extracted nodes and relationships should be formatted as instances of the 
provided Node and Relationship classes.
Ensure that the extracted data adheres to the structure defined by the classes.
Output the structured data in a format that can be easily validated against 
the provided code.

Instructions for you:
Read the provided content thoroughly.
Identify distinct entities mentioned in the content and categorize them as 
nodes.
Determine relationships between these entities and represent them as directed 
relationships, including a timestamp for each relationship.
Provide the extracted nodes and relationships in the specified format below.
Example for you:

Example Content:
"John works at XYZ Corporation since 2020. He is a software engineer. The 
company is located in New York City."

Expected Output:

Nodes:

Node(id='John', type='Person')
Node(id='XYZ Corporation', type='Organization')
Node(id='New York City', type='Location')

Relationships:

Relationship(subj=Node(id='John', type='Person'), obj=Node(id='XYZ 
Corporation', type='Organization'), type='WorksAt', timestamp='1717193166')
Relationship(subj=Node(id='John', type='Person'), obj=Node(id='New York City', 
type='Location'), type='ResidesIn', timestamp='1719700236')

===== TASK =====
Please extracts nodes and relationships from given content and structures them 
into Node and Relationship objects. 

{task}
"""


ans_custom_str = kg_agent.run(
    element_example, parse_graph_elements=False, prompt=custom_prompt
)
ans_custom_GraphElement = kg_agent.run(
    element_example, parse_graph_elements=True, prompt=custom_prompt
)


# Get custom str output
print(ans_custom_str)

# Get custom GraphElement output
print(ans_custom_GraphElement)

"""
===============================================================================
### Nodes:

1. Node(id='CAMEL-AI.org', type='Organization')
2. Node(id='open-source community', type='Community')
3. Node(id='autonomous agents', type='Concept')
4. Node(id='communicative agents', type='Concept')

### Relationships:

1. Relationship(subj=Node(id='CAMEL-AI.org', type='Organization'), 
obj=Node(id='open-source community', type='Community'), type='IsPartOf',
timestamp='1717193166')
2. Relationship(subj=Node(id='open-source community', type='Community'), 
obj=Node(id='autonomous agents', type='Concept'), type='Studies',
timestamp='1719700236')
3. Relationship(subj=Node(id='open-source community', type='Community'), 
obj=Node(id='communicative agents', type='Concept'), type='Studies',
timestamp='1719700236')
===============================================================================
"""

"""
===============================================================================
nodes=[
Node(id='CAMEL-AI.org', type='Organization',
properties={'source': 'agent_created'}), 
Node(id='open-source community', type='Community',
properties={'source': 'agent_created'}), 
Node(id='autonomous agents', type='Concept',
properties={'source': 'agent_created'}), 
Node(id='communicative agents', type='Concept',
properties={'source': 'agent_created'})] 
relationships=[Relationship(subj=Node(id='CAMEL-AI.org', type='Organization', 
properties={'source': 'agent_created'}), 
obj=Node(id='open-source community', type='Community',
properties={'source': 'agent_created'}),
type="IsA', timestamp='1717193166", properties={'source': 'agent_created'}), 
Relationship(subj=Node(id='open-source community', type='Community', 
properties={'source': 'agent_created'}), 
obj=Node(id='autonomous agents', type='Concept', 
properties={'source': 'agent_created'}), type="Studies',
timestamp='1719700236", 
properties={'source': 'agent_created'}),
Relationship(subj=Node(id='open-source community', type='Community', 
properties={'source': 'agent_created'}), 
obj=Node(id='communicative agents', type='Concept', 
properties={'source': 'agent_created'}), 
type="Studies', timestamp='1719700236",
properties={'source': 'agent_created'})] 
source=<unstructured.documents.elements.Text object at 0x7f1583ee7d30>
===============================================================================
"""
