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


# Step 1: Define helper functions
def check_node_exists(nebula_graph, node_id: str) -> bool:
    """Check if a node exists in the Nebula Graph."""
    query = (
        f'LOOKUP ON player WHERE player.name == "{node_id}" YIELD id(vertex);'
    )
    result = nebula_graph.query(query)
    return result.row_size() > 0


def check_relationship_exists(
    nebula_graph, subj: str, obj: str, rel_type: str
) -> bool:
    """Check if a specific relationship exists between two nodes."""
    query = f'GO FROM "{subj}" OVER {rel_type} WHERE $$.team.name == "{obj}" YIELD edge AS rel;'
    result = nebula_graph.query(query)
    return result.row_size() > 0


# Step 2: Initialize the NebulaGraph client
host = '127.0.0.1'
username = 'root'
password = 'nebula'
space = 'demo_basketballplayer'

nebula_graph = NebulaGraph(host, username, password, space)

# Step 3: Ensure necessary tags (node types) and edge types exist
nebula_graph.ensure_tag_exists("player")
nebula_graph.ensure_tag_exists("team")
nebula_graph.ensure_edge_type_exists("BelongsTo")

# Step 4: Check if the node 'Lionel Messi' exists
query = 'DELETE VERTEX "player_lm"'
nebula_graph.query(query)

if check_node_exists(nebula_graph, "Lionel Messi"):
    print("Node 'Lionel Messi' already exists.")
else:
    print("Node 'Lionel Messi' does not exist. Proceeding to add it...")

# Step 5: Create and add graph elements for 'Lionel Messi'
player_node = Node(
    id="player_lm",
    type="player",
    properties={"name": "Lionel Messi", "age": 36},
)
team_node = Node(
    id="Paris_Saint-Germain",
    type="team",
    properties={"name": "Paris Saint-Germain"},
)

graph_elements = [
    GraphElement(
        nodes=[player_node, team_node],
        relationships=[
            Relationship(
                subj=Node(id="Lionel Messi", type="player"),
                obj=Node(id="Paris Saint-Germain", type="team"),
                type="BelongsTo",
            )
        ],
        source=Element(element_id="a05b820b51c760a41415c57c1eef8f08"),
    )
]

print("Adding Lionel Messi -> Paris Saint-Germain relationship...")
nebula_graph.add_graph_elements(graph_elements)

# Step 6: Verify that the node and relationship were successfully added

# Check node existence
if check_node_exists(nebula_graph, "Lionel Messi"):
    print("Node 'Lionel Messi' added successfully.")
else:
    print("Failed to add node 'Lionel Messi'.")

# Check relationship existence
if check_relationship_exists(
    nebula_graph, "Lionel Messi", "Paris Saint-Germain", "BelongsTo"
):
    print(
        "Relationship 'Lionel Messi -> Paris Saint-Germain' (BelongsTo) added successfully."
    )
else:
    print("Failed to add relationship 'Lionel Messi -> Paris Saint-Germain'.")

# Step 7: Delete the triplet (Lionel Messi -> Paris Saint-Germain -> BelongsTo)
print(
    "Attempting to delete Lionel Messi -> Paris Saint-Germain relationship..."
)

nebula_graph.delete_triplet("player_lm", "Paris_Saint-Germain", "BelongsTo")

# Step 8: Re-check node and relationship existence after deletion

# Re-check node existence
if not check_node_exists(nebula_graph, "Lionel Messi"):
    print("Node 'Lionel Messi' deleted successfully.")
else:
    print("Failed to delete node 'Lionel Messi'.")

# Re-check relationship existence
if not check_relationship_exists(
    nebula_graph, "Lionel Messi", "Paris Saint-Germain", "BelongsTo"
):
    print(
        "Relationship 'Lionel Messi -> Paris Saint-Germain' (BelongsTo) deleted successfully."
    )
else:
    print(
        "Failed to delete relationship 'Lionel Messi -> Paris Saint-Germain'."
    )

# Step 9: Add another triplet for 'Lionel Messi -> Barcelona'
print("Adding Lionel Messi -> Barcelona relationship...")

nebula_graph.add_triplet(
    player_node,
    team_node,
    "BelongsTo",
)


# Check if the new triplet has been added successfully
if check_node_exists(nebula_graph, "Lionel Messi"):
    print("Node 'Lionel Messi' added successfully.")
else:
    print("Failed to add node 'Lionel Messi'.")

if check_relationship_exists(
    nebula_graph, "Lionel Messi", "Barcelona", "BelongsTo"
):
    print(
        "Relationship 'Lionel Messi -> Barcelona' (BelongsTo) added successfully."
    )
else:
    print("Failed to add relationship 'Lionel Messi -> Barcelona'.")

"""
===============================================================================
Node 'Lionel Messi' does not exist. Proceeding to add it...
Adding Lionel Messi -> Paris Saint-Germain relationship...
Node 'Lionel Messi' added successfully.
Failed to add relationship 'Lionel Messi -> Paris Saint-Germain'.
Attempting to delete Lionel Messi -> Paris Saint-Germain relationship...
Node 'Lionel Messi' deleted successfully.
Relationship 'Lionel Messi -> Paris Saint-Germain' (BelongsTo) deleted successfully.
Adding Lionel Messi -> Barcelona relationship...
Node 'Lionel Messi' added successfully.
Failed to add relationship 'Lionel Messi -> Barcelona'.
 ==============================================================================
"""
