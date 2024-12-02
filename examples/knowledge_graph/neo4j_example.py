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
from camel.storages import Neo4jGraph

# Set Neo4j instance
n4j = Neo4jGraph(
    url="Your Url", username="Your Username", password="Your Password"
)

# Add triplet into database
n4j.add_triplet(subj="CAMEL", obj="multi-agent framework", rel="belongs to")

# Run a Cypher query
print(n4j.query("""MATCH (n) RETURN n AS node"""))

"""
===============================================================================
[{'node': {'id': 'CAMEL'}}, {'node': {'id': 'multi-agent framework'}}]
===============================================================================
"""

# Get schema from database
print(n4j.get_schema)

"""
===============================================================================
Node properties are the following:
Entity {id: STRING}
Relationship properties are the following:

The relationships are the following:
(:Entity)-[:BELONGS_TO]->(:Entity)
===============================================================================
"""

# Get structured schema from database
print(n4j.get_structured_schema)

"""
===============================================================================
{'node_props': {'Entity': [{'property': 'id', 'type': 'STRING'}]},
 'rel_props': {}, 'relationships': [{'start': 'Entity', 'type': 'BELONGS_TO',
 'end': 'Entity'}], 'metadata': {'constraint': [], 'index': [{'id': 0, 'name':
 'index_343aff4e', 'state': 'ONLINE', 'populationPercent': 100.0, 'type':
 'LOOKUP', 'entityType': 'NODE', 'labelsOrTypes': None, 'properties': None,
 'indexProvider': 'token-lookup-1.0', 'owningConstraint': None, 'lastRead':
 neo4j.time.DateTime(2024, 5, 22, 15, 12, 27, 452000000, tzinfo=UTC),
 'readCount': 675297, 'trackedSince': neo4j.time.DateTime(2024, 3, 17, 6, 31,
 29, 925000000, tzinfo=UTC), 'options': {'indexProvider': 'token-lookup-1.0',
 'indexConfig': {}}, 'failureMessage': '', 'createStatement': 'CREATE LOOKUP
 INDEX index_343aff4e FOR (n) ON EACH labels(n)'}, {'id': 1, 'name':
 'index_f7700477', 'state': 'ONLINE', 'populationPercent': 100.0, 'type':
 'LOOKUP', 'entityType': 'RELATIONSHIP', 'labelsOrTypes': None, 'properties'
 None, 'indexProvider': 'token-lookup-1.0', 'owningConstraint': None,
 'lastRead': neo4j.time.DateTime(2024, 5, 22, 15, 9, 41, 917000000,
 tzinfo=UTC), 'readCount': 16, 'trackedSince': neo4j.time.DateTime(2024, 3,
 17, 6, 31, 29, 939000000, tzinfo=UTC), 'options': {'indexProvider':
 'token-lookup-1.0', 'indexConfig': {}}, 'failureMessage': '',
 'createStatement': 'CREATE LOOKUP INDEX index_f7700477 FOR ()-[r]-() ON EACH
 type(r)'}]}}
 ==============================================================================
"""
