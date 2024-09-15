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

from nebula3.Config import Config  # type:ignore[import]
from nebula3.gclient.net import ConnectionPool, Session  # type:ignore[import]

from camel.storages.graph_storages.base import BaseGraphStorage
from camel.storages.graph_storages.graph_element import (
    GraphElement,
)
from camel.utils.commons import dependencies_required

BASE_ENTITY_LABEL = "__Entity__"


class NebulaGraph(BaseGraphStorage):
    @dependencies_required('nebula3')
    def __init__(
        self, host, username, password, space, port=9669, timeout=10000
    ):
        self.host = host
        self.username = username
        self.password = password
        self.space = space
        self.timeout = timeout
        self.port = port
        self.connection_pool = self._init_connection_pool()
        self.schema: str = ""
        self.structured_schema: Dict[str, Any] = {}

    def _init_connection_pool(self):
        """Initialize the connection pool."""
        config = Config()
        config.max_connection_pool_size = 10  # Set the connection pool size
        config.timeout = self.timeout

        # Create the connection pool
        connection_pool = ConnectionPool()

        # Initialize the connection pool with Nebula Graph's address and port
        if not connection_pool.init([(self.host, self.port)], config):
            raise Exception("Failed to initialize the connection pool")

        return connection_pool

    def _get_session(self) -> Session:
        """Get a session from the connection pool."""
        session = self.connection_pool.get_session(
            self.username, self.password
        )
        if not session:
            raise Exception("Failed to create a session")

        # Use the specified space
        session.execute(f"use {self.space};")
        return session

    def query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query the graph store with statement and parameters.

        Args:
            query (str): The query to be executed.
            params (Optional[Dict[str, Any]]): A dictionary of parameters to be used in the query.
                                                Defaults to `None`.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing rows of results.
        """
        session = None
        try:
            # Get the session
            session = self._get_session()
            result_set = session.execute(query)
            return result_set

        except Exception as e:
            raise ValueError(f"Query execution error: {e!s}")

        # finally:
        #     # Ensure the session is closed after the query
        #     if session:
        #         session.release()

    def get_node_properties(self):
        # Query all tags
        result = self.query('SHOW TAGS')
        node_schema_props = []
        node_structure_props = []

        # Iterate through each tag to get its properties
        for row in result.rows():
            tag_name = row.values[0].get_sVal().decode('utf-8')
            describe_result = self.query(f'DESCRIBE TAG {tag_name}')
            properties = []

            for prop_row in describe_result.rows():
                prop_name = prop_row.values[0].get_sVal().decode('utf-8')
                node_schema_props.append(f"{tag_name}.{prop_name}")
                properties.append(prop_name)

            node_structure_props.append(
                {"labels": tag_name, "properties": properties}
            )

        return node_schema_props, node_structure_props

    def get_relationship_properties(self):
        # Query all edge types
        result = self.query('SHOW EDGES')
        rel_schema_props = []
        rel_structure_props = []

        # Iterate through each edge type to get its properties
        for row in result.rows():
            edge_name = row.values[0].get_sVal().decode('utf-8')
            describe_result = self.query(f'DESCRIBE EDGE {edge_name}')
            properties = []

            for prop_row in describe_result.rows():
                prop_name = prop_row.values[0].get_sVal().decode('utf-8')
                rel_schema_props.append(f"{edge_name}.{prop_name}")
                properties.append(prop_name)

            rel_structure_props.append(
                {"type": edge_name, "properties": properties}
            )

        return rel_schema_props, rel_structure_props

    def get_relationship_types(self):
        # Query all edge types
        result = self.query('SHOW EDGES')
        rel_types = []

        # Extract relationship type names
        for row in result.rows():
            edge_name = row.values[0].get_sVal().decode('utf-8')
            rel_types.append(edge_name)

        return rel_types

    def add_graph_elements(
        self,
        graph_elements: List[GraphElement],
        include_source: bool = False,
        base_entity_label: bool = False,
    ) -> None:
        nodes = self.extract_nodes(graph_elements)
        for node in nodes:
            self.ensure_tag_exists(node['type'])
            self.add_node(node['id'], node['type'])

        relationships = self.extract_relationships(graph_elements)
        for rel in relationships:
            self.ensure_edge_type_exists(rel['type'])
            self.add_relationship(
                rel['subj']['id'], rel['obj']['id'], rel['type']
            )

    def add_relationship(self, src_id, dst_id, edge_type):
        # Add relationship
        insert_stmt = (
            f'INSERT EDGE `{edge_type}`() VALUES "{src_id}"->"{dst_id}":()'
        )
        res = self.query(insert_stmt)
        if not res.is_succeeded():
            print(
                f'create  relationship `{src_id}` -> `{dst_id}` failed: {res.error_msg()}'
            )

    def ensure_edge_type_exists(self, edge_type):
        # Check if Edge Type exists
        result = self.query('SHOW EDGES')
        if result.is_succeeded():
            edges = [
                row.values[0].get_sVal().decode('utf-8')
                for row in result.rows()
            ]
            if edge_type not in edges:
                # Create a new Edge Type
                create_edge_stmt = f'CREATE EDGE `{edge_type}`()'
                res = self.query(create_edge_stmt)
                if not res.is_succeeded():
                    print(
                        f'create Edge Type `{edge_type}` failed: {res.error_msg()}'
                    )
        else:
            print(f'execute SHOW EDGES failed: {result.error_msg()}')

    def ensure_tag_exists(self, tag_name):
        # Check if Tag exists
        result = self.query('SHOW TAGS')
        if result.is_succeeded():
            tags = [
                row.values[0].get_sVal().decode('utf-8')
                for row in result.rows()
            ]
            if tag_name not in tags:
                # Create a new Tag
                create_tag_stmt = f'CREATE TAG `{tag_name}`()'
                res = self.query(create_tag_stmt)
                if not res.is_succeeded():
                    print(f'create Tag `{tag_name}` failed: {res.error_msg()}')
        else:
            print(f'execute SHOW TAGS failed: {result.error_msg()}')

    def add_node(self, node_id, tag_name):
        # Add node
        insert_stmt = f'INSERT VERTEX `{tag_name}`() VALUES "{node_id}":()'
        res = self.query(insert_stmt)
        if not res.is_succeeded():
            print(f'add node `{node_id}` failed: {res.error_msg()}')

    def extract_nodes(self, graph_elements):
        nodes = []
        seen_nodes = set()
        for graph_element in graph_elements:
            for node in graph_element.nodes:
                node_key = (node.id, node.type)
                if node_key not in seen_nodes:
                    nodes.append({'id': node.id, 'type': node.type})
                    seen_nodes.add(node_key)
        return nodes

    def extract_relationships(self, graph_elements):
        relationships = []
        for graph_element in graph_elements:
            for rel in graph_element.relationships:
                relationship_dict = {
                    'subj': {'id': rel.subj.id, 'type': rel.subj.type},
                    'obj': {'id': rel.obj.id, 'type': rel.obj.type},
                    'type': rel.type,
                }
                relationships.append(relationship_dict)
        return relationships

    def refresh_schema(self) -> None:
        self.schema = self.get_schema()
        self.structured_schema = self.get_structured_schema()

    def get_structured_schema(self):
        _, node_properties = self.get_node_properties()

        # 2. Get relationship properties and types
        _, rel_properties = self.get_relationship_properties()

        # 3. Get relationship types
        relationships = self.get_relationship_types()

        # 4. Get metadata (e.g., constraints and indexes)
        constraint = self.get_constraints()
        index = self.get_indexes()

        # Build structured_schema
        structured_schema = {
            "node_props": {
                el["labels"]: el["properties"] for el in node_properties
            },
            "rel_props": {
                el["type"]: el["properties"] for el in rel_properties
            },
            "relationships": relationships,
            "metadata": {"constraint": constraint, "index": index},
        }

        return structured_schema

    def get_schema(self):
        # Get all node and relationship properties
        formatted_node_props, _ = self.get_node_properties()
        formatted_rel_props, _ = self.get_relationship_properties()
        formatted_rels = self.get_relationship_types()

        # Generate schema string
        schema = "\n".join(
            [
                "Node properties are the following:",
                ", ".join(formatted_node_props),
                "Relationship properties are the following:",
                ", ".join(formatted_rel_props),
                "The relationships are the following:",
                ", ".join(formatted_rels),
            ]
        )

        return schema

    def get_indexes(self):
        result = self.query('SHOW TAG INDEXES')
        indexes = []

        # Get tag indexes
        for row in result.rows():
            index_name = row.values[0].get_sVal().decode('utf-8')
            indexes.append(index_name)

        return indexes

    def get_constraints(self):
        # Nebula currently does not support constraint queries, return empty
        return []
