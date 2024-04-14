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
from unstructured.documents.elements import Element

from camel.storages import Neo4jGraph
from camel.storages.graph_storages.graph_document import GraphDocument, Node, Relationship
from camel.storages.graph_storages.neo4j_graph import (
    BASE_ENTITY_LABEL,
    NODE_PROPERTY_QUERY,
    REL_PROPERTY_QUERY,
    REL_QUERY,
)

test_data = [
    GraphDocument(
        nodes=[Node(id="foo", type="foo"), Node(id="bar", type="bar")],
        relationships=[
            Relationship(
                source=Node(id="foo", type="foo"),
                target=Node(id="bar", type="bar"),
                type="REL",
            )
        ],
            source=Element(element_id="a04b820b51c760a41415c57c1eef8f08").to_dict())
]

NEO4J_URI="neo4j+s://5af77aab.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="SEK_Fx5Bx-BkRwMx6__zM_TOPqXLWEP-czuIZ_u7-zE"

# def test_cypher_return_correct_schema() -> None:
#     r"""Test that chain returns direct results."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(
#         url=url,
#         username=username,
#         password=password,
#     )
#     # Delete all nodes in the graph
#     graph.query("MATCH (n) DETACH DELETE n")
#     # Create two nodes and a relationship
#     graph.query(
#         """
#         CREATE (la:LabelA {property_a: 'a'})
#         CREATE (lb:LabelB)
#         CREATE (lc:LabelC)
#         MERGE (la)-[:REL_TYPE]-> (lb)
#         MERGE (la)-[:REL_TYPE {rel_prop: 'abc'}]-> (lc)
#         """
#     )
#     # Refresh schema information
#     graph.refresh_schema()

#     node_properties = graph.query(
#         NODE_PROPERTY_QUERY, params={"EXCLUDED_LABELS": [BASE_ENTITY_LABEL]}
#     )
#     relationships_properties = graph.query(
#         REL_PROPERTY_QUERY, params={"EXCLUDED_LABELS": [BASE_ENTITY_LABEL]}
#     )
#     relationships = graph.query(
#         REL_QUERY, params={"EXCLUDED_LABELS": [BASE_ENTITY_LABEL]}
#     )

#     expected_node_properties = [
#         {
#             "output": {
#                 "properties": [{"property": "property_a", "type": "STRING"}],
#                 "labels": "LabelA",
#             }
#         }
#     ]
#     expected_relationships_properties = [
#         {
#             "output": {
#                 "type": "REL_TYPE",
#                 "properties": [{"property": "rel_prop", "type": "STRING"}],
#             }
#         }
#     ]
#     expected_relationships = [
#         {"output": {"start": "LabelA", "type": "REL_TYPE", "end": "LabelB"}},
#         {"output": {"start": "LabelA", "type": "REL_TYPE", "end": "LabelC"}},
#     ]

#     assert node_properties == expected_node_properties
#     assert relationships_properties == expected_relationships_properties
#     # Order is not guaranteed with Neo4j returns
#     assert (
#         sorted(relationships, key=lambda x: x["output"]["end"])
#         == expected_relationships
#     )


# def test_neo4j_timeout() -> None:
#     r"""Test that neo4j uses the timeout correctly."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(url=url, username=username, password=password, timeout=0.1)
#     try:
#         graph.query("UNWIND range(0,100000,1) AS i MERGE (:Foo {id:i})")
#     except Exception as e:
#         assert (
#             e.code  # type: ignore[attr-defined]
#             == "Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration"
#         )


# def test_neo4j_sanitize_values() -> None:
#     r"""Test that neo4j uses the timeout correctly."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(url=url, username=username, password=password, sanitize=True)
#     # Delete all nodes in the graph
#     graph.query("MATCH (n) DETACH DELETE n")
#     # Create two nodes and a relationship
#     graph.query(
#         """
#         CREATE (la:LabelA {property_a: 'a'})
#         CREATE (lb:LabelB)
#         CREATE (lc:LabelC)
#         MERGE (la)-[:REL_TYPE]-> (lb)
#         MERGE (la)-[:REL_TYPE {rel_prop: 'abc'}]-> (lc)
#         """
#     )
#     graph.refresh_schema()

#     output = graph.query("RETURN range(0,130,1) AS result")
#     assert output == [{}]


# def test_neo4j_add_data() -> None:
#     r"""Test that neo4j correctly import graph document."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(url=url, username=username, password=password, sanitize=True)
#     # Delete all nodes in the graph
#     graph.query("MATCH (n) DETACH DELETE n")
#     # Remove all constraints
#     graph.query("CALL apoc.schema.assert({}, {})")
#     graph.refresh_schema()
#     # Create two nodes and a relationship
#     graph.add_graph_documents(test_data)
#     output = graph.query(
#         "MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY label"
#     )
#     assert output == [{"label": ["bar"], "count": 1}, {"label": ["foo"], "count": 1}]
#     assert graph.structured_schema["metadata"]["constraint"] == []


def test_neo4j_add_data_source() -> None:
    """Test that neo4j correctly import graph document with source."""
    url = NEO4J_URI
    username = NEO4J_USERNAME
    password = NEO4J_PASSWORD
    assert url is not None
    assert username is not None
    assert password is not None

    graph = Neo4jGraph(url=url, username=username, password=password, sanitize=True)
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Remove all constraints
    graph.query("CALL apoc.schema.assert({}, {})")
    graph.refresh_schema()
    # Create two nodes and a relationship
    graph.add_graph_documents(test_data, include_source=True)
    output = graph.query(
        "MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY label"
    )
    assert output == [
        {"label": ["Element"], "count": 1},
        {"label": ["bar"], "count": 1},
        {"label": ["foo"], "count": 1},
    ]
    assert graph.structured_schema["metadata"]["constraint"] == []


# def test_neo4j_add_data_base() -> None:
#     r"""Test that neo4j correctly import graph document with base_entity."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(url=url, username=username, password=password, sanitize=True)
#     # Delete all nodes in the graph
#     graph.query("MATCH (n) DETACH DELETE n")
#     # Remove all constraints
#     graph.query("CALL apoc.schema.assert({}, {})")
#     graph.refresh_schema()
#     # Create two nodes and a relationship
#     graph.add_graph_documents(test_data, base_entity_label=True)
#     output = graph.query(
#         "MATCH (n) RETURN apoc.coll.sort(labels(n)) AS label, "
#         "count(*) AS count ORDER BY label"
#     )
#     assert output == [
#         {"label": [BASE_ENTITY_LABEL, "bar"], "count": 1},
#         {"label": [BASE_ENTITY_LABEL, "foo"], "count": 1},
#     ]
#     assert graph.structured_schema["metadata"]["constraint"] != []


# def test_neo4j_add_data_base_source() -> None:
#     """Test that neo4j correctly import graph document with base_entity and source."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(url=url, username=username, password=password, sanitize=True)
#     # Delete all nodes in the graph
#     graph.query("MATCH (n) DETACH DELETE n")
#     # Remove all constraints
#     graph.query("CALL apoc.schema.assert({}, {})")
#     graph.refresh_schema()
#     # Create two nodes and a relationship
#     graph.add_graph_documents(test_data, base_entity_label=True, include_source=True)
#     output = graph.query(
#         "MATCH (n) RETURN apoc.coll.sort(labels(n)) AS label, "
#         "count(*) AS count ORDER BY label"
#     )
#     assert output == [
#         {"label": ["Element"], "count": 1},
#         {"label": [BASE_ENTITY_LABEL, "bar"], "count": 1},
#         {"label": [BASE_ENTITY_LABEL, "foo"], "count": 1},
#     ]
#     assert graph.structured_schema["metadata"]["constraint"] != []


# def test_neo4j_filtering_labels() -> None:
#     r"""Test that neo4j correctly filters excluded labels."""
#     url = NEO4J_URI
#     username = NEO4J_USERNAME
#     password = NEO4J_PASSWORD
#     assert url is not None
#     assert username is not None
#     assert password is not None

#     graph = Neo4jGraph(url=url, username=username, password=password, sanitize=True)
#     # Delete all nodes in the graph
#     graph.query("MATCH (n) DETACH DELETE n")
#     # Remove all constraints
#     graph.query("CALL apoc.schema.assert({}, {})")
#     graph.query(
#         "CREATE (:`_Bloom_Scene_`)-[:_Bloom_HAS_SCENE_]->(:`_Bloom_Perspective_`)"
#     )
#     graph.refresh_schema()

#     # Assert both are empty
#     assert graph.structured_schema["node_props"] == {}
#     assert graph.structured_schema["relationships"] == []
