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

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from nebula3.data.ResultSet import (  # type: ignore[import-untyped]
        ResultSet,
    )
    from nebula3.gclient.net import (  # type: ignore[import-untyped]
        ConnectionPool,
        Session,
    )

from camel.storages.graph_storages.base import BaseGraphStorage
from camel.storages.graph_storages.graph_element import (
    GraphElement,
)
from camel.utils.commons import dependencies_required


@dependencies_required('nebula3')
class NebulaGraph(BaseGraphStorage):
    def __init__(
        self, host, username, password, space, port=9669, timeout=10000
    ):
        r"""Initializes the NebulaGraph client.

        Args:
            host (str): The host address of the NebulaGraph service.
            username (str): The username for authentication.
            password (str): The password for authentication.
            space (str): The graph space to use.
            port (int, optional): The port number for the connection.
                (default: :obj:`9669`)
            timeout (int, optional): The connection timeout in milliseconds.
                (default: :obj:`10000`)
        """
        self.host = host
        self.username = username
        self.password = password
        self.space = space
        self.timeout = timeout
        self.port = port
        self.schema: str = ""
        self.structured_schema: Dict[str, Any] = {}
        self.connection_pool = self._init_connection_pool()
        self.session = self._get_session()

    def _init_connection_pool(self) -> "ConnectionPool":
        r"""Initialize the connection pool.

        Returns:
            ConnectionPool: A connection pool instance.

        Raises:
            Exception: If the connection pool initialization fails.
        """
        from nebula3.Config import Config  # type: ignore[import-untyped]
        from nebula3.gclient.net import ConnectionPool

        config = Config()
        config.max_connection_pool_size = 10
        config.timeout = self.timeout

        # Create the connection pool
        connection_pool = ConnectionPool()

        # Initialize the connection pool with Nebula Graph's address and port
        if not connection_pool.init([(self.host, self.port)], config):
            raise Exception("Failed to initialize the connection pool")

        return connection_pool

    def _get_session(self) -> "Session":
        r"""Get a session from the connection pool.

        Returns:
            Session: A session object connected to NebulaGraph.

        Raises:
            Exception: If session creation or space usage fails.
        """
        session = self.connection_pool.get_session(
            self.username, self.password
        )
        if not session:
            raise Exception("Failed to create a session")

        # Use the specified space
        session.execute(
            f"CREATE SPACE IF NOT EXISTS {self.space} (vid_type=FIXED_STRING(30));"
        )
        session.execute(f"USE {self.space};")
        return session

    @property
    def get_client(self) -> Any:
        r"""Get the underlying graph storage client."""
        return self

    def query(self, query: str) -> "ResultSet":  # type:ignore[override]
        r"""Execute a query on the graph store.

        Args:
            query (str): The Cypher-like query to be executed.

        Returns:
            ResultSet: The result set of the query execution.

        Raises:
            ValueError: If the query execution fails.
        """
        try:
            # Get the session
            result_set = self.session.execute(query)
            return result_set

        except Exception as e:
            raise ValueError(f"Query execution error: {e!s}")

    def get_node_properties(self) -> Tuple[List[str], List[Dict[str, Any]]]:
        r"""Retrieve node properties from the graph.

        Returns:
            Tuple[List[str], List[Dict[str, Any]]]: A tuple where the first
                element is a list of node schema properties, and the second
                element is a list of dictionaries representing node structures.
        """
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

    def get_relationship_properties(
        self,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        r"""Retrieve relationship (edge) properties from the graph.

        Returns:
            Tuple[List[str], List[Dict[str, Any]]]: A tuple where the first
                element is a list of relationship schema properties, and the
                second element is a list of dictionaries representing
                relationship structures.
        """

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

    def get_relationship_types(self) -> List[str]:
        r"""Retrieve relationship types from the graph.

        Returns:
            List[str]: A list of relationship (edge) type names.
        """
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
    ) -> None:
        r"""Add graph elements (nodes and relationships) to the graph.

        Args:
            graph_elements (List[GraphElement]): A list of graph elements
                containing nodes and relationships.
        """
        nodes = self.extract_nodes(graph_elements)
        for node in nodes:
            self.ensure_tag_exists(node['type'])
            self.add_node(node['id'], node['type'], node['properties'])

        relationships = self._extract_relationships(graph_elements)
        for rel in relationships:
            self.ensure_edge_type_exists(rel['type'])
            self.add_relationship(
                rel['subj']['id'], rel['obj']['id'], rel['type']
            )

    def add_relationship(
        self, src_id: str, dst_id: str, edge_type: str
    ) -> None:
        r"""Add a relationship (edge) between two nodes in the graph.

        Args:
            src_id (str): The source node ID.
            dst_id (str): The destination node ID.
            edge_type (str): The relationship (edge) type.
        """
        # Add relationship
        insert_stmt = (
            f'INSERT EDGE `{edge_type}`() VALUES "{src_id}"->"{dst_id}":()'
        )
        res = self.query(insert_stmt)
        if not res.is_succeeded():
            print(
                f'create relationship `{src_id}` -> `{dst_id}`'
                + f'failed: {res.error_msg()}'
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
                    print(f'create Edge failed: {res.error_msg()}')
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

    def add_node(
        self,
        node_id: str,
        tag_name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Add a node with the specified tag and properties.

        Args:
            node_id (str): The ID of the node.
            tag_name (str): The tag name of the node.
            properties (Optional[Dict[str, Any]]): A dictionary of node
                properties.
        """

        if properties:
            prop_names = ", ".join(properties.keys())
            prop_values = ", ".join(
                f'"{v}"' if isinstance(v, str) else str(v)
                for v in properties.values()
            )
            insert_stmt = f'INSERT VERTEX [IF NOT EXISTS] {tag_name}({prop_names}) VALUES "{node_id}":({prop_values})'
        else:
            insert_stmt = f'INSERT VERTEX [IF NOT EXISTS] {tag_name}() VALUES "{node_id}":()'

        try:
            res = self.query(insert_stmt)
            if not res.is_succeeded():
                print(f'Add node `{node_id}` failed: {res.error_msg()}')
        except Exception as e:
            print(f'Error while adding node `{node_id}`: {e}')

    def extract_nodes(self, graph_elements: List[Any]) -> List[Dict]:
        r"""Extracts unique nodes from graph elements.

        Args:
            graph_elements (List[Any]): A list of graph elements containing
                nodes.

        Returns:
            List[Dict]: A list of dictionaries representing nodes.
        """
        nodes = []
        seen_nodes = set()
        for graph_element in graph_elements:
            for node in graph_element.nodes:
                node_key = (node.id, node.type)
                if node_key not in seen_nodes:
                    nodes.append(
                        {
                            'id': node.id,
                            'type': node.type,
                            'properties': node.properties,
                        }
                    )
                    seen_nodes.add(node_key)
        return nodes

    def _extract_relationships(self, graph_elements: List[Any]) -> List[Dict]:
        r"""Extracts relationships from graph elements.

        Args:
            graph_elements (List[Any]): A list of graph elements containing
                relationships.

        Returns:
            List[Dict]: A list of dictionaries representing relationships.
        """
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
        r"""Refreshes the schema by fetching the latest schema details."""
        self.schema = self.get_schema()
        self.structured_schema = self.get_structured_schema

    @property
    @abstractmethod
    def get_structured_schema(self) -> Dict[str, Any]:
        r"""Generates a structured schema consisting of node and relationship
        properties, relationships, and metadata.

        Returns:
            Dict[str, Any]: A dictionary representing the structured schema.
        """
        _, node_properties = self.get_node_properties()
        _, rel_properties = self.get_relationship_properties()
        relationships = self.get_relationship_types()
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
            "metadata": {"index": index},
        }

        return structured_schema

    def get_schema(self):
        r"""Generates a schema string describing node and relationship
        properties and relationships.

        Returns:
            str: A string describing the schema.
        """
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
        r"""Fetches the tag indexes from the database.

        Returns:
            List[str]: A list of tag index names.
        """
        result = self.query('SHOW TAG INDEXES')
        indexes = []

        # Get tag indexes
        for row in result.rows():
            index_name = row.values[0].get_sVal().decode('utf-8')
            indexes.append(index_name)

        return indexes

    def add_triplet(
        self,
        subj: str,
        obj: str,
        rel: str,
    ) -> None:
        r"""Adds a relationship (triplet) between two entities in the Nebula
        Graph database.

        Args:
            subj (str): The identifier for the subject entity.
            obj (str): The identifier for the object entity.
            rel (str): The relationship between the subject and object.
        """
        self.ensure_tag_exists(subj)
        self.ensure_tag_exists(obj)
        self.add_node(node_id=subj, tag_name=subj)
        self.add_node(node_id=obj, tag_name=obj)

        insert_stmt = f'INSERT EDGE `{rel}`() VALUES "{subj}"->"{obj}":();'
        self.query(insert_stmt)

    def delete_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Deletes a specific triplet (relationship between two entities)
        from the Nebula Graph database.

        Args:
            subj (str): The identifier for the subject entity.
            obj (str): The identifier for the object entity.
            rel (str): The relationship between the subject and object.
        """
        delete_edge_query = f'DELETE EDGE `{rel}` "{subj}"->"{obj}";'
        self.query(delete_edge_query)

        if not self._check_edges(subj):
            self.delete_entity(subj)
        if not self._check_edges(obj):
            self.delete_entity(obj)

    def delete_entity(self, entity_id: str) -> None:
        r"""Deletes an entity (vertex) from the graph.

        Args:
            entity_id (str): The identifier of the entity to be deleted.
        """
        delete_vertex_query = f'DELETE VERTEX "{entity_id}";'
        self.query(delete_vertex_query)

    def _check_edges(self, entity_id: str) -> bool:
        r"""Checks if an entity has any remaining edges in the graph.

        Args:
            entity_id (str): The identifier of the entity.

        Returns:
            bool: :obj:`True` if the entity has edges, :obj:`False` otherwise.
        """
        # Combine the outgoing and incoming edge count query
        check_query = f"""
        (GO FROM {entity_id} OVER * YIELD count(*) as out_count) 
        UNION 
        (GO FROM {entity_id} REVERSELY OVER * YIELD count(*) as in_count)
        """

        # Execute the query
        result = self.query(check_query)

        # Check if the result contains non-zero edges
        if result.is_succeeded():
            rows = result.rows()
            total_count = sum(int(row.values[0].get_iVal()) for row in rows)
            return total_count > 0
        else:
            return False
