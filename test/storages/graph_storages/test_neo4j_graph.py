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
import os

import pytest
from unstructured.documents.elements import Element

from camel.storages import Neo4jGraph
from camel.storages.graph_storages.graph_element import (
    GraphElement,
    Node,
    Relationship,
)
from camel.storages.graph_storages.neo4j_graph import (
    BASE_ENTITY_LABEL,
    NODE_PROPERTY_QUERY,
    REL_PROPERTY_QUERY,
    REL_QUERY,
)

url = os.environ.get("NEO4J_URI", "Your_URI")
username = os.environ.get("NEO4J_USERNAME", "Your_Username")
password = os.environ.get("NEO4J_PASSWORD", "Your_Password")


test_data = [
    GraphElement(
        nodes=[
            Node(id="id_subj", type="type_subj"),
            Node(id="id_obj", type="type_obj"),
        ],
        relationships=[
            Relationship(
                subj=Node(id="id_subj", type="type_subj"),
                obj=Node(id="id_obj", type="type_obj"),
                type="type_rel",
            )
        ],
        source=Element(element_id="a04b820b51c760a41415c57c1eef8f08"),
    )
]


def test_cypher_return_correct_schema() -> None:
    r"""Test that chain returns direct results.
    Tested graph.query and graph.refresh_schema.
    """
    graph = Neo4jGraph(
        url=url,
        username=username,
        password=password,
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Create two nodes and a relationship
    graph.query("""
        CREATE (la:LabelA {property_a: 'a'})
        CREATE (lb:LabelB)
        CREATE (lc:LabelC)
        MERGE (la)-[:REL_TYPE]-> (lb)
        MERGE (la)-[:REL_TYPE {rel_prop: 'abc'}]-> (lc)
        """)
    # Refresh schema information
    graph.refresh_schema()

    node_properties = graph.query(
        NODE_PROPERTY_QUERY, params={"EXCLUDED_LABELS": [BASE_ENTITY_LABEL]}
    )
    relationships_properties = graph.query(
        REL_PROPERTY_QUERY, params={"EXCLUDED_LABELS": [BASE_ENTITY_LABEL]}
    )
    relationships = graph.query(
        REL_QUERY, params={"EXCLUDED_LABELS": [BASE_ENTITY_LABEL]}
    )

    expected_node_properties = [
        {
            "output": {
                "properties": [{"property": "property_a", "type": "STRING"}],
                "labels": "LabelA",
            }
        }
    ]
    expected_relationships_properties = [
        {
            "output": {
                "type": "REL_TYPE",
                "properties": [{"property": "rel_prop", "type": "STRING"}],
            }
        }
    ]
    expected_relationships = [
        {"output": {"start": "LabelA", "type": "REL_TYPE", "end": "LabelB"}},
        {"output": {"start": "LabelA", "type": "REL_TYPE", "end": "LabelC"}},
    ]

    assert node_properties == expected_node_properties
    assert relationships_properties == expected_relationships_properties
    # Order is not guaranteed with Neo4j returns
    assert (
        sorted(relationships, key=lambda x: x["output"]["end"])
        == expected_relationships
    )


def test_neo4j_timeout() -> None:
    r"""Test that neo4j uses the timeout correctly."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, timeout=5
    )
    try:
        graph.query("UNWIND range(0,100000,1) AS i MERGE (:Foo {id:i})")
    except Exception as e:
        assert (
            e.code  # type: ignore[attr-defined]
            in [
                "Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration",
                "Neo.ClientError.Transaction.LockClientStopped",
            ]
        )


def test_neo4j_truncate_values() -> None:
    r"""Test that neo4j uses the timeout correctly."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Create two nodes and a relationship
    graph.query("""
        CREATE (la:LabelA {property_a: 'a'})
        CREATE (lb:LabelB)
        CREATE (lc:LabelC)
        MERGE (la)-[:REL_TYPE]-> (lb)
        MERGE (la)-[:REL_TYPE {rel_prop: 'abc'}]-> (lc)
        """)
    graph.refresh_schema()

    output = graph.query("RETURN range(0,130,1) AS result")
    assert output == [{}]


def test_neo4j_add_data() -> None:
    r"""Test that neo4j correctly import graph element."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Remove all constraints
    graph.query("CALL apoc.schema.assert({}, {})")
    graph.refresh_schema()
    # Create two nodes and a relationship
    graph.add_graph_elements(test_data)
    output = graph.query(
        "MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY label"
    )
    assert output == [
        {"label": ["type_obj"], "count": 1},
        {"label": ["type_subj"], "count": 1},
    ]
    assert graph.structured_schema["metadata"]["constraint"] == []


def test_neo4j_add_data_source() -> None:
    r"""Test that neo4j correctly import graph element with source."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Remove all constraints
    graph.query("CALL apoc.schema.assert({}, {})")
    graph.refresh_schema()
    # Create two nodes and a relationship
    graph.add_graph_elements(test_data, include_source=True)
    output = graph.query(
        "MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY label"
    )
    assert output == [
        {"label": ["Element"], "count": 1},
        {"label": ["type_obj"], "count": 1},
        {"label": ["type_subj"], "count": 1},
    ]
    assert graph.structured_schema["metadata"]["constraint"] == []


def test_neo4j_add_data_base() -> None:
    r"""Test that neo4j correctly import graph element with base_entity."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Remove all constraints
    graph.query("CALL apoc.schema.assert({}, {})")
    graph.refresh_schema()
    # Create two nodes and a relationship
    graph.add_graph_elements(test_data, base_entity_label=True)
    output = graph.query(
        "MATCH (n) RETURN apoc.coll.sort(labels(n)) AS label, "
        "count(*) AS count ORDER BY label"
    )
    assert output == [
        {"label": [BASE_ENTITY_LABEL, "type_obj"], "count": 1},
        {"label": [BASE_ENTITY_LABEL, "type_subj"], "count": 1},
    ]
    assert graph.structured_schema["metadata"]["constraint"] != []


def test_neo4j_add_data_base_source() -> None:
    r"""Test that neo4j correctly import graph element with base_entity and
    source."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Remove all constraints
    graph.query("CALL apoc.schema.assert({}, {})")
    graph.refresh_schema()
    # Create two nodes and a relationship
    graph.add_graph_elements(
        test_data, base_entity_label=True, include_source=True
    )
    output = graph.query(
        "MATCH (n) RETURN apoc.coll.sort(labels(n)) AS label, "
        "count(*) AS count ORDER BY label"
    )
    assert output == [
        {"label": ["Element"], "count": 1},
        {"label": [BASE_ENTITY_LABEL, "type_obj"], "count": 1},
        {"label": [BASE_ENTITY_LABEL, "type_subj"], "count": 1},
    ]
    assert graph.structured_schema["metadata"]["constraint"] != []


def test_neo4j_filtering_labels() -> None:
    r"""Test that neo4j correctly filters excluded labels."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Remove all constraints
    graph.query("CALL apoc.schema.assert({}, {})")
    graph.query(
        "CREATE (:`Excluded_Label_A`)-[:`Excluded_Rel_A`]->"
        "(:`Excluded_Label_B`)"
    )
    graph.refresh_schema()

    # Assert both are empty
    assert graph.structured_schema["node_props"] == {}
    assert graph.structured_schema["relationships"] == []


@pytest.mark.skip(reason="Skipping since need GDS installation")
def test_random_walk_with_restarts() -> None:
    r"""Test the random walk with restarts sampling algorithm."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Create sample graph
    graph.query("""
        CREATE (n1:Node {id: 1})
        CREATE (n2:Node {id: 2})
        CREATE (n3:Node {id: 3})
        CREATE (n1)-[:REL_TYPE]->(n2)
        CREATE (n2)-[:REL_TYPE]->(n3)
    """)
    # Run random walk with restarts
    result = graph.random_walk_with_restarts(
        graph_name="sample_graph",
        sampling_ratio=0.5,
        start_node_ids=[1],
        restart_probability=0.15,
    )
    assert "graphName" in result
    assert result["nodeCount"] > 0


@pytest.mark.skip(reason="Skipping since need GDS installation")
def test_common_neighbour_aware_random_walk() -> None:
    r"""Test the common neighbour aware random walk sampling algorithm."""
    graph = Neo4jGraph(
        url=url, username=username, password=password, truncate=True
    )
    # Delete all nodes in the graph
    graph.query("MATCH (n) DETACH DELETE n")
    # Create sample graph
    graph.query("""
        CREATE (n1:Node {id: 1})
        CREATE (n2:Node {id: 2})
        CREATE (n3:Node {id: 3})
        CREATE (n1)-[:REL_TYPE]->(n2)
        CREATE (n2)-[:REL_TYPE]->(n3)
    """)
    # Run common neighbour aware random walk
    result = graph.common_neighbour_aware_random_walk(
        graph_name="sample_graph", sampling_ratio=0.5, start_node_ids=[1]
    )
    assert "graphName" in result
    assert result["nodeCount"] > 0
