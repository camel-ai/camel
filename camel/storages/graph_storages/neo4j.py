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

from typing import Any, Dict, List, Optional

from camel.storages import BaseGraphStorage

NODE_PROPERTIES_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
  AND NOT label IN [$BASE_ENTITY_LABEL]
WITH label AS nodeLabels, collect({property:property, type:type}) AS properties
RETURN {labels: nodeLabels, properties: properties} AS output

"""

REL_PROPERTIES_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
WITH label AS nodeLabels, collect({property:property, type:type}) AS properties
RETURN {type: nodeLabels, properties: properties} AS output
"""

REL_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE type = "RELATIONSHIP" AND elementType = "node"
UNWIND other AS other_node
RETURN {start: label, type: property, end: toString(other_node)} AS output
"""

INCLUDE_DOCS_QUERY = ("CREATE (d:Document) "
                      "SET d.text = $document.page_content "
                      "SET d += $document.metadata "
                      "WITH d ")

MERGE_SOURCE_QUERY = """MERGE (d)-[:MENTIONS]->(source) """

BASE_ENTITY_LABEL = "__Entity__"


class Neo4jGraphStore(BaseGraphStorage):

    def __init__(
        self,
        username: str,
        password: str,
        url: str,
        database: str = "neo4j",
        node_label: str = "Entity",
        **kwargs: Any,
    ) -> None:

        try:
            import neo4j
        except ImportError as e:
            raise ImportError("Package `neo4j` not installed.") from e

        self.node_label = node_label
        self._driver = neo4j.GraphDatabase.driver(url,
                                                  auth=(username, password))
        self._database = database
        self.schema = ""
        self.structured_schema: Dict[str, Any] = {}

        # Verify connection
        try:
            self._driver.verify_connectivity()
        except neo4j.exceptions.ServiceUnavailable:
            raise ValueError("Could not connect to Neo4j database. "
                             "Please ensure that the url is correct")
        except neo4j.exceptions.AuthError:
            raise ValueError(
                "Could not connect to Neo4j database. "
                "Please ensure that the username and password are correct")

        # Set schema
        try:
            self.refresh_schema()
        except neo4j.exceptions.ClientError:
            raise ValueError(
                "Could not use APOC procedures. "
                "Please ensure the APOC plugin is installed in Neo4j and that "
                "'apoc.meta.data()' is allowed in Neo4j configuration ")

        # Create constraint for faster insert and retrieval
        try:  # Using Neo4j 5
            self.query("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (n:%s) REQUIRE n.id IS
                       UNIQUE;
                """ % (self.node_label))
        except Exception:  # Using Neo4j <5
            self.query("""
                CREATE CONSTRAINT IF NOT EXISTS ON (n:%s) ASSERT n.id IS
                       UNIQUE;
                """ % (self.node_label))

    @property
    def client(self) -> Any:
        return self._driver

    @property
    def get_schema(self) -> str:
        r"""Get the schema of the Neo4jGraph store."""
        return self.schema

    def refresh_schema(self) -> None:
        r"""Refreshes the Neo4j graph schema information."""
        from neo4j.exceptions import ClientError

        node_properties = [
            el["output"] for el in self.query(NODE_PROPERTIES_QUERY)
        ]
        rel_properties = [
            el["output"] for el in self.query(REL_PROPERTIES_QUERY)
        ]
        relationships = [el["output"] for el in self.query(REL_QUERY)]

        # Get constraints & indexes
        try:
            constraint = self.query("SHOW CONSTRAINTS")
            index = self.query("SHOW INDEXES YIELD *")
        except (
                ClientError
        ):  # Read-only user might not have access to schema information
            constraint = []
            index = []

        self.structured_schema = {
            "node_props":
            {el["labels"]: el["properties"]
             for el in node_properties},
            "rel_props":
            {el["type"]: el["properties"]
             for el in rel_properties},
            "relationships": relationships,
            "metadata": {
                "constraint": constraint,
                "index": index
            },
        }

        # Format node properties
        formatted_node_props = []
        for el in node_properties:
            props_str = ", ".join([
                f"{prop['property']}: {prop['type']}"
                for prop in el["properties"]
            ])
            formatted_node_props.append(f"{el['labels']} {{{props_str}}}")

        # Format relationship properties
        formatted_rel_props = []
        for el in rel_properties:
            props_str = ", ".join([
                f"{prop['property']}: {prop['type']}"
                for prop in el["properties"]
            ])
            formatted_rel_props.append(f"{el['type']} {{{props_str}}}")

        # Format relationships
        formatted_rels = [
            f"(:{el['start']})-[:{el['type']}]->(:{el['end']})"
            for el in relationships
        ]

        self.schema = "\n".join([
            "Node properties are the following:",
            ",".join(formatted_node_props),
            "Relationship properties are the following:",
            ",".join(formatted_rel_props),
            "The relationships are the following:",
            ",".join(formatted_rels),
        ])

    def _get_node_import_query(self, baseEntityLabel: bool,
                               include_source: bool) -> str:
        if baseEntityLabel:
            return (
                f"{INCLUDE_DOCS_QUERY if include_source else ''}"
                "UNWIND $data AS row "
                f"MERGE (source:`{BASE_ENTITY_LABEL}` {{id: row.id}}) "
                "SET source += row.properties "
                f"{MERGE_SOURCE_QUERY if include_source else ''}"
                "WITH source, row "
                "CALL apoc.create.addLabels( source, [row.type] ) YIELD node "
                "RETURN distinct 'done' AS result")
        else:
            return (
                f"{INCLUDE_DOCS_QUERY if include_source else ''}"
                "UNWIND $data AS row "
                "CALL apoc.merge.node([row.type], {id: row.id}, "
                "row.properties, {}) YIELD node "
                f"{'MERGE (d)-[:MENTIONS]->(node) ' if include_source else ''}"
                "RETURN distinct 'done' AS result")

    def _get_rel_import_query(self, baseEntityLabel: bool) -> str:
        if baseEntityLabel:
            return ("UNWIND $data AS row "
                    f"MERGE (source:`{BASE_ENTITY_LABEL}` {{id: row.source}}) "
                    f"MERGE (target:`{BASE_ENTITY_LABEL}` {{id: row.target}}) "
                    "WITH source, target, row "
                    "CALL apoc.merge.relationship(source, row.type, "
                    "{}, row.properties, target) YIELD rel "
                    "RETURN distinct 'done'")
        else:
            return (
                "UNWIND $data AS row "
                "CALL apoc.merge.node([row.source_label], {id: row.source},"
                "{}, {}) YIELD node as source "
                "CALL apoc.merge.node([row.target_label], {id: row.target},"
                "{}, {}) YIELD node as target "
                "CALL apoc.merge.relationship(source, row.type, "
                "{}, row.properties, target) YIELD rel "
                "RETURN distinct 'done'")

    def add(
        self,
        graph_documents: List[Any],
        include_source: bool = False,
        baseEntityLabel: bool = False,
    ) -> None:
        r"""
        This method constructs nodes and relationships in the graph based on
        the provided GraphDocument objects.

        Parameters:
        graph_documents (List[GraphDocument]): A list of GraphDocument objects
            that contain the nodes and relationships to be added to the graph.
            Each GraphDocument should encapsulate the structure of part of the
            graph, including nodes, relationships, and the source document
            information.
        include_source (bool, optional): If True, stores the source document
            and links it to nodes in the graph using the MENTIONS relationship.
            This is useful for tracing back the origin of data. Defaults to
            False.
        baseEntityLabel (bool, optional): If True, each newly created node
            gets a secondary __Entity__ label, which is indexed and improves
            import speed and performance. Defaults to False.
        """
        if baseEntityLabel:  # Check if constraint already exists
            constraint_exists = any([
                el["labelsOrTypes"] == [BASE_ENTITY_LABEL]
                and el["properties"] == ["id"]
                for el in self.structured_schema.get("metadata", {}).get(
                    "constraint")
            ])
            if not constraint_exists:
                # Create constraint
                self.query(f"""CREATE CONSTRAINT IF NOT EXISTS FOR """
                           f"""(b:{BASE_ENTITY_LABEL}) """
                           "REQUIRE b.id IS UNIQUE;")
                self.refresh_schema()  # Refresh constraint information

        node_import_query = self._get_node_import_query(
            baseEntityLabel, include_source)
        rel_import_query = self._get_rel_import_query(baseEntityLabel)
        for document in graph_documents:
            # Import nodes
            self.query(
                node_import_query,
                {
                    "data": [el.__dict__ for el in document.nodes],
                    "document": document.source.__dict__,
                },
            )
            # Import relationships
            self.query(
                rel_import_query,
                {
                    "data": [{
                        "source": el.source.id,
                        "source_label": el.source.type,
                        "target": el.target.id,
                        "target_label": el.target.type,
                        "type": el.type.replace(" ", "_").upper(),
                        "properties": el.properties,
                    } for el in document.relationships]
                },
            )

    def query(self, query: str, param_map: Optional[Dict[str,
                                                         Any]] = {}) -> Any:
        with self._driver.session(database=self._database) as session:
            result = session.run(query, param_map)
            return [d.data() for d in result]
