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

from unstructured.documents.elements import Element

from camel.storages.graph_storages import NebulaGraph
from camel.storages.graph_storages.graph_element import (
    GraphElement,
    Node,
    Relationship,
)

# Step 2: Initialize the NebulaGraph client
host = '127.0.0.1'
username = 'root'
password = 'nebula'
space = 'space_name'

nebula_graph = NebulaGraph(host, username, password, space)

# Ensure necessary tags (node types) exist
nebula_graph.ensure_tag_exists("CAMEL_AI")
nebula_graph.ensure_tag_exists("Agent_Framework")

# Show existing tags
query = 'SHOW TAGS;'
print(nebula_graph.query(query))

"""
==============================================================================
ResultSet(keys: ['Name'], values: ["CAMEL_AI"],["Agent_Framework"])
==============================================================================
"""

# Add triplet
nebula_graph.add_triplet(
    subj="CAMEL_AI", obj="Agent_Framework", rel="contribute_to"
)

# Check structured schema
print(nebula_graph.get_structured_schema)

"""
==============================================================================
{'node_props': {'CAMEL_AI': [], 'Agent_Framework': []}, 'rel_props': 
{'contribute_to': []}, 'relationships': ['contribute_to'], 'metadata': 
{'index': []}}
==============================================================================
"""

# Delete triplet
nebula_graph.delete_triplet(
    subj="CAMEL_AI", obj="Agent_Framework", rel="contribute_to"
)

# Create and add graph element
node_camel = Node(
    id="CAMEL_AI",
    type="Agent_Framework",
)
node_nebula = Node(
    id="Nebula",
    type="Graph_Database",
)

graph_elements = [
    GraphElement(
        nodes=[node_camel, node_nebula],
        relationships=[
            Relationship(
                subj=node_camel,
                obj=node_nebula,
                type="Supporting",
            )
        ],
        source=Element(element_id="a05b820b51c760a41415c57c1eef8f08"),
    )
]

# Add this graph element to graph db
nebula_graph.add_graph_elements(graph_elements)

# Get structured schema
print(nebula_graph.get_structured_schema)

"""
==============================================================================
{'node_props': {'Agent_Framework': [], 'CAMEL_AI': [], 'Graph_Database': [], 
'Nebula': [], 'agent_framework': []}, 'rel_props': {'Supporting': [], 
'contribute_to': []}, 'relationships': ['Supporting', 'contribute_to'], 
'metadata': {'index': []}}
==============================================================================
"""
