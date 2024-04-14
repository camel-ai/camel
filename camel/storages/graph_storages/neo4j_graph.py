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
import logging
from hashlib import md5
from typing import Any, Dict, List, Optional

from camel.storages.graph_storages import GraphDocument

logger = logging.getLogger(__name__)

BASE_ENTITY_LABEL = "__Entity__"
EXCLUDED_LABELS = ["_Bloom_Perspective_", "_Bloom_Scene_"]
EXCLUDED_RELS = ["_Bloom_HAS_SCENE_"]

NODE_PROPERTY_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
AND NOT label IN $EXCLUDED_LABELS
WITH label AS nodeLabels, collect({property:property, type:type}) AS properties
RETURN {labels: nodeLabels, properties: properties} AS output
"""

REL_PROPERTY_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
AND NOT label IN $EXCLUDED_LABELS
WITH label AS nodeLabels, collect({property:property, type:type}) AS properties
RETURN {type: nodeLabels, properties: properties} AS output
"""

REL_QUERY = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE type = "RELATIONSHIP" AND elementType = "node"
UNWIND other AS other_node
WITH * WHERE NOT label IN $EXCLUDED_LABELS
    AND NOT other_node IN $EXCLUDED_LABELS
RETURN {start: label, type: property, end: toString(other_node)} AS output
"""

INCLUDE_DOCS_QUERY = ("MERGE (d:Element {id:$document['element_id']}) "
                      "SET d.text = $document['text'] "
                      "SET d += $document['metadata'] "
                      "WITH d ")


LIST_LIMIT = 128


class Neo4jGraph():
    r"""Provides a connection to a Neo4j database for various graph operations.

    The detailed information about Neo4j is available at:
    `Neo4j https://neo4j.com/docs/getting-started/>`

    This module used the work of Langchian and Llamaindex as reference.

    Args:
        url (str): The URL of the Neo4j database server.
        username (str): The username for database authentication.
        password (str): The password for database authentication.
        database (str): The name of the database to connect to. Defaults to
            `neo4j`.
        timeout (Optional[float]): The timeout for transactions in seconds.
            Useful for terminating long-running queries. Defaults to `None`.
        sanitize (bool): A flag to indicate whether to remove lists with more
            than `LIST_LIMIT` elements from results. Defaults to `False`.
    """

    def __init__(
        self,
        url: str = "",
        username: str = "",
        password: str = "",
        database: str = "neo4j",
        timeout: Optional[float] = None,
        sanitize: bool = False,
    ) -> None:
        r"""Create a new Neo4j graph instance."""
        try:
            import neo4j
        except ImportError:
            raise ValueError("Could not import neo4j python package. "
                             "Please install it with `pip install neo4j`.")

        self.driver = neo4j.GraphDatabase.driver(url,
                                                 auth=(username, password))
        self.database = database
        self.timeout = timeout
        self.sanitize = sanitize
        self.schema: str = ""
        self.structured_schema: Dict[str, Any] = {}

        # Verify connection
        try:
            self.driver.verify_connectivity()
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

    @property
    def client(self) -> Any:
        return self.driver

    @property
    def get_schema(self, refresh: bool = False) -> str:
        r"""Retrieve the schema of the Neo4jGraph store.

        Args:
            refresh (bool): A flag indicating whether to forcibly refresh the
                schema from the Neo4jGraph store regardless of whether it is
                already cached. Defaults to `False`.

        Returns:
            str: The schema of the Neo4jGraph store.
        """
        if self.schema and not refresh:
            return self.schema
        self.refresh_schema()
        logger.debug(f"get_schema() schema:\n{self.schema}")
        return self.schema

    @property
    def get_structured_schema(self) -> Dict[str, Any]:
        r"""Returns the structured schema of the graph

        Returns:
            dict[str, any]: The structured schema of the graph.
        """
        return self.structured_schema

    def _value_sanitize(self, d: Any) -> Any:
        r"""Sanitizes the input dictionary `d` by removing entries that are
        dictionaries with values resembling embeddings and lists containing
        more than `LIST_LIMIT` elements. This method aims to reduce unnecessary
        computational cost and noise in scenarios where such detailed data
        structures are not needed, for example, in simplifying data for
        processing by a language model.

        Args:
            d (Any): The dictionary to be sanitized.

        Returns:
            Any: The sanitized dictionary, with embedding-like
                dictionaries and oversized lists handled.
        """
        if isinstance(d, dict):
            new_dict = {}
            for key, value in d.items():
                if isinstance(value, dict):
                    sanitized_value = self._value_sanitize(value)
                    # Check if the sanitized value is not None
                    if (sanitized_value is not None):
                        new_dict[key] = sanitized_value
                elif isinstance(value, list):
                    if len(value) < LIST_LIMIT:
                        sanitized_value = self._value_sanitize(value)
                        # Check if the sanitized value is not None
                        if (sanitized_value is not None):
                            new_dict[key] = sanitized_value
                    # Do not include the key if the list is oversized
                else:
                    new_dict[key] = value
            return new_dict
        elif isinstance(d, list):
            if len(d) < LIST_LIMIT:
                return [
                    self._value_sanitize(item) for item in d
                    if self._value_sanitize(item) is not None
                ]
            else:
                return None
        else:
            return d

    def query(self, query: str,
              params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        r"""Executes a Cypher query against a Neo4j database and returns the
        results.

        Args:
            query (str): The Cypher query to be executed.
            params (Optional[Dict[str, Any]]): A dictionary of parameters to
                be used in the query. Defaults to None.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each
                dictionary represents a row of results from the Cypher query.
                The keys are the column names, and the values are the
                corresponding values for that column.

        Raises:
            ValueError: If the executed Cypher query syntax is invalid.
        """
        from neo4j import Query
        from neo4j.exceptions import CypherSyntaxError

        if params is None:
            params = {}

        with self.driver.session(database=self.database) as session:
            try:
                data = session.run(Query(text=query, timeout=self.timeout),
                                   params)
                json_data = [r.data() for r in data]
                if self.sanitize:
                    json_data = [self._value_sanitize(el) for el in json_data]
                return json_data
            except CypherSyntaxError as e:
                raise ValueError(
                    f"Generated Cypher Statement is not valid\n{e}")

    def refresh_schema(self) -> None:
        r"""Refreshes the Neo4j graph schema information by querying the
        database for node properties, relationship properties, and
        relationships.
        """
        from neo4j.exceptions import ClientError

        # Extract schema elements from the database
        node_properties = [
            el["output"] for el in self.query(
                NODE_PROPERTY_QUERY, params={
                    "EXCLUDED_LABELS": EXCLUDED_LABELS + [BASE_ENTITY_LABEL]
                })
        ]
        rel_properties = [
            el["output"] for el in self.query(
                REL_PROPERTY_QUERY, params={"EXCLUDED_LABELS": EXCLUDED_RELS})
        ]
        relationships = [
            el["output"] for el in self.query(
                REL_QUERY, params={
                    "EXCLUDED_LABELS": EXCLUDED_LABELS + [BASE_ENTITY_LABEL]
                })
        ]

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
            }
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

    def add_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Adds a relationship (triplet) between two entities in the database.

        Args:
            subj (str): The identifier for the subject entity.
            obj (str): The identifier for the object entity.
            rel (str): The relationship between the subject and object.
        """
        query = """
            MERGE (n1:`%s` {id:$subj})
            MERGE (n2:`%s` {id:$obj})
            MERGE (n1)-[:`%s`]->(n2)
        """

        prepared_statement = query % (
            BASE_ENTITY_LABEL.replace("_", ""),
            BASE_ENTITY_LABEL.replace("_", ""),
            rel.replace(" ", "_").upper(),
        )

        # Execute the query within a database session
        with self.driver.session(database=self.database) as session:
            session.run(prepared_statement, {"subj": subj, "obj": obj})

    def _delete_rel(self, subj: str, obj: str, rel: str) -> None:
        r"""Deletes a specific relationship between two nodes in the Neo4j
        database.

        Args:
            subj (str): The identifier for the subject entity.
            obj (str): The identifier for the object entity.
            rel (str): The relationship between the subject and object to
                delete.
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                ("MATCH (n1:{})-[r:{}]->(n2:{}) WHERE n1.id = $subj AND n2.id"
                 " = $obj DELETE r").format(BASE_ENTITY_LABEL.replace("_", ""),
                                            rel,
                                            BASE_ENTITY_LABEL.replace("_",
                                                                      "")),
                {
                    "subj": subj,
                    "obj": obj
                },
            )

    def _delete_entity(self, entity: str) -> None:
        r"""Deletes an entity from the Neo4j database based on its unique
        identifier.

        Args:
            entity (str): The unique identifier of the entity to be deleted.
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                "MATCH (n:%s) WHERE n.id = $entity DELETE n" %
                BASE_ENTITY_LABEL.replace("_", ""),
                {"entity": entity},
            )

    def _check_edges(self, entity: str) -> bool:
        r"""Checks if the given entity has any relationships in the graph
        database.

        Args:
            entity (str): The unique identifier of the entity to check.

        Returns:
            bool: True if the entity has at least one edge (relationship),
                False otherwise.
        """
        with self.driver.session(database=self.database) as session:
            is_exists_result = session.run(
                "MATCH (n1:%s)--() WHERE n1.id = $entity RETURN count(*)" %
                (BASE_ENTITY_LABEL.replace("_", "")),
                {"entity": entity},
            )
            return bool(list(is_exists_result))

    def delete_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Deletes a specific triplet from the graph, comprising a subject,
        object and relationship.

        Args:
            subj (str): The identifier for the subject entity.
            obj (str): The identifier for the object entity.
            rel (str): The relationship between the subject and object.
        """
        self._delete_rel(subj, obj, rel)
        if not self._check_edges(subj):
            self._delete_entity(subj)
        if not self._check_edges(obj):
            self._delete_entity(obj)

    def _get_node_import_query(self, base_entity_label: bool,
                               include_source: bool) -> str:
        r"""Constructs a Cypher query string for importing nodes into a Neo4j
        database.

        Args:
            base_entity_label (bool): Flag indicating whether to use a base
                entity label in the MERGE operation.
            include_source (bool): Flag indicating whether to include source
                document information in the query.

        Returns:
            str: A Cypher query string tailored based on the provided flags.
        """
        if base_entity_label:
            return (
                f"{INCLUDE_DOCS_QUERY if include_source else ''}"
                "UNWIND $data AS row "
                f"MERGE (source:`{BASE_ENTITY_LABEL}` {{id: row.id}}) "
                "SET source += row.properties "
                f"{'MERGE (d)-[:MENTIONS]->(source) ' if include_source else ''}"
                "WITH source, row "
                "CALL apoc.create.addLabels( source, [row.type] ) YIELD node "
                "RETURN distinct 'done' AS result"
            )
        else:
            return (
                f"{INCLUDE_DOCS_QUERY if include_source else ''}"
                "UNWIND $data AS row "
                "CALL apoc.merge.node([row.type], {id: row.id}, "
                "row.properties, {}) YIELD node "
                f"{'MERGE (d)-[:MENTIONS]->(node) ' if include_source else ''}"
                "RETURN distinct 'done' AS result"
            )

    def _get_rel_import_query(self, base_entity_label: bool) -> str:
        r"""Constructs a Cypher query string for importing relationship into a
        Neo4j database.

        Args:
            base_entity_label (bool): Flag indicating whether to use a base
                entity label in the MERGE operation.

        Returns:
            str: A Cypher query string tailored based on the provided flags.
        """
        if base_entity_label:
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

    def add_graph_documents(
        self,
        graph_documents: List[GraphDocument],
        include_source: bool = False,
        base_entity_label: bool = False,
    ) -> None:
        r"""Adds nodes and relationships from a list of GraphDocument objects
        to the graph database.

        Args:
            graph_documents (List[GraphDocument]): A list of GraphDocument
                objects that contain the nodes and relationships to be added
                to the graph. Each GraphDocument should encapsulate the
                structure of part of the graph, including nodes,
                relationships, and the source document information.
            include_source (bool, optional): If True, stores the source
                document and links it to nodes in the graph using the MENTIONS
                relationship. This is useful for tracing back the origin of
                data. Merges source documents based on the `id` property from
                the source document metadata if available; otherwise it
                calculates the MD5 hash of `page_content` for merging process.
                Defaults to False.
            base_entity_label (bool, optional): If True, each newly created
                node gets a secondary `BASE_ENTITY_LABEL` label, which is
                indexed and improves import speed and performance. Defaults to
                False.
        """
        if base_entity_label:  # check if constraint already exists
            constraint_exists = any([
                el["labelsOrTypes"] == [BASE_ENTITY_LABEL]
                and el["properties"] == ["id"]
                for el in self.structured_schema.get("metadata", {}).get(
                    "constraint")
            ])
            if not constraint_exists:
                # Create constraint
                self.query("CREATE CONSTRAINT IF NOT EXISTS FOR"
                           f"(b:{BASE_ENTITY_LABEL}) "
                           "REQUIRE b.id IS UNIQUE;")
                self.refresh_schema()  # refresh constraint information

        node_import_query = self._get_node_import_query(
            base_entity_label, include_source)
        rel_import_query = self._get_rel_import_query(base_entity_label)
        for document in graph_documents:
            if not document.source['element_id']:
                document.source['element_id'] = md5(
                    str(document).encode("utf-8")).hexdigest()

            # Import nodes
            self.query(
                node_import_query,
                {
                    "data": [el.__dict__ for el in document.nodes],
                    "document": document.source,
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
