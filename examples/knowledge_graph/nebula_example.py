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
# Import required modules
from unstructured.documents.elements import Element

from camel.storages.graph_storages.graph_element import (
    GraphElement,
    Node,
    Relationship,
)
from camel.storages.graph_storages.nebula_graph import NebulaGraph

# Step 1: Initialize the NebulaGraph client
host = '127.0.0.1'
username = 'root'
password = 'nebula'
space = 'demo_basketballplayer'

nebula_graph = NebulaGraph(host, username, password, space)

# Step 2: Ensure necessary tags (node types) and edge types exist
nebula_graph.ensure_tag_exists("player")
nebula_graph.ensure_tag_exists("team")
nebula_graph.ensure_edge_type_exists("BelongsTo")

# Step 3: Create and add graph elements
graph_elements = [
    GraphElement(
        nodes=[
            Node(id="LeBron James", type="player"),
            Node(id="Los Angeles Lakers", type="team"),
        ],
        relationships=[
            Relationship(
                subj=Node(id="LeBron James", type="player"),
                obj=Node(id="Los Angeles Lakers", type="team"),
                type="BelongsTo",
            )
        ],
        source=Element(element_id="a05b820b51c760a41415c57c1eef8f08"),
    )
]

nebula_graph.add_graph_elements(graph_elements)

# Step 4: Get and check structured schema
structured_schema = nebula_graph.get_structured_schema()

if (
    'player' in structured_schema['node_props']
    and 'team' in structured_schema['node_props']
):
    print("Nodes 'player' and 'team' added successfully.")
else:
    print("Failed to add nodes 'player' and 'team'.")

if 'BelongsTo' in structured_schema['relationships']:
    print("Relationship 'BelongsTo' added successfully.")
else:
    print("Failed to add relationship 'BelongsTo'.")

# Step 5: Add a triplet (Michael Jordan -> Chicago Bulls -> BelongsTo)
nebula_graph.add_triplet(
    "Michael Jordan",
    "Chicago Bulls",
    "BelongsTo",
    subj_tag="player",
    obj_tag="team",
)

structured_schema = nebula_graph.get_structured_schema()

if (
    'player' in structured_schema['node_props']
    and 'team' in structured_schema['node_props']
):
    print("Nodes 'player' and 'team' for triplet added successfully.")
else:
    print("Failed to add nodes for the triplet.")

if 'BelongsTo' in structured_schema['relationships']:
    print(
        r'''Triplet 'Michael Jordan' -> 'Chicago Bulls' (BelongsTo) added 
        successfully.'''
    )
else:
    print("Failed to add triplet 'Michael Jordan' -> 'Chicago Bulls'.")

# Step 6: Delete the triplet (LeBron James -> Los Angeles Lakers -> BelongsTo)
try:
    nebula_graph.delete_triplet(
        "LeBron James", "Los Angeles Lakers", "BelongsTo"
    )
except Exception as e:
    print(f"Failed to delete triplet: {e}")

print(
    r'''Triplet 'LeBron James' -> 'Los Angeles Lakers' (BelongsTo) deleted 
    successfully.'''
)

print(nebula_graph.get_structured_schema())
"""
===============================================================================
Nodes 'player' and 'team' added successfully.
Relationship 'BelongsTo' added successfully.
Nodes 'player' and 'team' for triplet added successfully.
Triplet 'Michael Jordan' -> 'Chicago Bulls' (BelongsTo) added 
        successfully.
Triplet 'LeBron James' -> 'Los Angeles Lakers' (BelongsTo) deleted 
    successfully.
{'node_props': {'player': ['name', 'age'], 'team': ['name']}, 'rel_props': 
{'BelongsTo': [], 'follow': ['degree'], 'serve': ['start_year', 'end_year']}, 
'relationships': ['BelongsTo', 'follow', 'serve'], 'metadata': {'constraint': 
[], 'index': ['player_index_0', 'player_index_1']}}
 ==============================================================================
"""
