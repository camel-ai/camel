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
import enum
import logging
import uuid
from typing import List, Optional

from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    ElementMetadata,
    Text,
)

from camel.embeddings import BaseEmbedding, OpenAIEmbedding
from camel.memories.base import MemoryBlock
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.graph_storages import BaseGraphStorage, Neo4jGraph
from camel.storages.graph_storages.graph_element import GraphElement
from camel.types import OpenAIBackendRole, RoleType

logger = logging.getLogger(__name__)


def convert_enums(obj):
    if isinstance(obj, enum.Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {k: convert_enums(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_enums(v) for v in obj]
    else:
        return obj


def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


class GraphDBBlock(MemoryBlock):
    r"""An implementation of the MemoryBlock abstract base
    class for maintaining and retrieving information using a
    graph database.

    Args:
        storage (BaseGraphStorage, optional): The storage mechanism
            for the graph database. Defaults to :obj:`Neo4jGraph`
            if not provided.
        embedding (BaseEmbedding, optional): Embedding mechanism to
            convert text into vector representations. Defaults
            to :obj:`OpenAIEmbedding`.
        url (str): URL for Neo4j database connection.
        username (str): Username for Neo4j database authentication.
        password (str): Password for Neo4j database authentication.
        database (str, optional): Name of the Neo4j database to use.
            Defaults to "neo4j".
    """

    def __init__(
        self,
        storage: Optional[BaseGraphStorage] = None,
        embedding: Optional[BaseEmbedding] = None,
        url: str = "http://localhost:7474/browser",
        username: str = "neo4j",
        password: str = "neo4j",
        database: Optional[str] = "neo4j",
    ) -> None:
        self.embedding = embedding or OpenAIEmbedding()
        self.storage: BaseGraphStorage
        if storage is None:
            if url and username and password:
                database = database if database is not None else "neo4j"
                self.storage = Neo4jGraph(url, username, password, database)
            else:
                raise ValueError(
                    """Either provide a storage instance or valid 
                    Neo4j connection parameters."""
                )
        else:
            self.storage = storage

        # Create vector index for Message embeddings
        try:
            self.storage.query(
                """
                CREATE VECTOR INDEX message_embeddings IF NOT EXISTS
                FOR (m:Message) ON (m.embedding)
                OPTIONS {indexConfig: {`vector.dimensions`: 1536, 
                `vector.similarity_function`: 'cosine'}}
                """
            )
            logger.info(
                "Vector index 'message_embeddings' created or already exists."
            )
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            raise

    def retrieve(
        self,
        query: Optional[str] = None,
        numberOfNearestNeighbours: int = 25,
    ) -> List[ContextRecord]:
        r"""Retrieves records from the graph database based on a query string
            or recent entries.

        Args:
            query (Optional[str]): A natural language query for
                similarity search.  If None, retrieves recent records.
            numberOfNearestNeighbours (int): The number of nearest neighbors
                to retrieve in similarity search, or the limit for default
                retrieval. Defaults to 25.

        Returns:
            List[ContextRecord]: A list of context records retrieved from the
            graph database.
        """
        try:
            if query:
                # Perform similarity search with embedding
                query_embedding = self.embedding.embed(query)
                results = self.storage.query(
                    """
                    CALL db.index.vector.queryNodes('message_embeddings', 
                    $k, $query_embedding)
                    YIELD node, score
                    WHERE node.embedding IS NOT NULL
                    RETURN node AS n, score AS similarity
                    ORDER BY score DESC
                    """,
                    {
                        "query_embedding": query_embedding,
                        "k": numberOfNearestNeighbours,
                    },
                )
            else:
                # Default retrieval of recent messages
                results = self.storage.query(
                    """
                    MATCH (n:Message)
                    RETURN n
                    ORDER BY n.timestamp DESC
                    LIMIT $k
                    """,
                    {"k": numberOfNearestNeighbours},
                )

            def reconstruct_from_flat(d):
                reconstructed = {}
                message = {}
                meta_dict = {}
                extra_info = {}

                for key, value in d.items():
                    if key == 'embedding':
                        continue
                    if value in ('__none__', None, ''):
                        value = None
                    elif value == '__empty_dict__':
                        value = {}
                    elif key.startswith('message_meta_dict_'):
                        meta_key = key[len('message_meta_dict_') :]
                        meta_dict[meta_key] = value
                    elif key.startswith('extra_info'):
                        extra_key = key[len('extra_info') :]
                        extra_info[extra_key] = value
                    elif key == 'role_at_backend' and value:
                        if value:
                            try:
                                value = (
                                    OpenAIBackendRole[value]
                                    if value
                                    in OpenAIBackendRole.__members__.values()
                                    else OpenAIBackendRole[value.upper()]
                                )
                            except (KeyError, ValueError) as e:
                                logger.error(
                                    f"""Invalid role_at_backend 
                                    value: {value}, error: {e}"""
                                )
                                value = None
                        reconstructed[key] = value
                    elif key.startswith('message_'):
                        sub_key = key[len('message_') :]
                        if sub_key == 'role_type' and value:
                            try:
                                value = (
                                    RoleType[value]
                                    if value in RoleType.__members__.values()
                                    else RoleType[value.upper()]
                                )
                            except (KeyError, ValueError) as e:
                                logger.error(
                                    f"""Invalid role_type value: 
                                    {value}, error: {e}"""
                                )
                                value = None
                        message[sub_key] = value
                    else:
                        reconstructed[key] = value
                message['meta_dict'] = (
                    meta_dict if meta_dict else {}
                )  # Ensure meta_dict is always present
                reconstructed['message'] = message
                reconstructed['extra_info'] = extra_info

                if 'agent_id' not in reconstructed:
                    reconstructed['agent_id'] = ''

                return reconstructed

            return [
                ContextRecord(
                    memory_record=MemoryRecord.from_dict(
                        reconstruct_from_flat(result["n"])
                    ),
                    score=result.get("similarity", 0),
                )
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error retrieving records: {e}")
            return []

    def write_records(self, records: List[MemoryRecord]) -> None:
        r"""Writes records to the graph database, extracting entities
            and relationships using KnowledgeGraphAgent.

        Args:
            records (List[MemoryRecord]): List of
            memory records to process and store.
        """
        from camel.agents import KnowledgeGraphAgent

        kg_agent = KnowledgeGraphAgent()
        for record in records:
            content = record.message.content
            if not isinstance(content, str):
                logger.error(f"Expected string content, got {type(content)}")
                continue

            element_id = record.to_dict().get('uuid', str(uuid.uuid4()))

            metadata_dict = {
                "timestamp": record.to_dict().get('timestamp', None),
                "role_at_backend": record.role_at_backend.name
                if record.role_at_backend
                else None,
                "agent_id": record.agent_id,
            }
            metadata_obj = ElementMetadata.from_dict(metadata_dict)

            element_class = TYPE_TO_TEXT_ELEMENT_MAP.get("NarrativeText", Text)
            element = element_class(
                text=content, element_id=element_id, metadata=metadata_obj
            )

            graph_element = kg_agent.run(element, parse_graph_elements=True)

            if not isinstance(graph_element, GraphElement):
                logger.error(
                    f"""Expected GraphElement, got 
                    {type(graph_element).__name__}: {graph_element}"""
                )
                continue

            # logging.info(f"graph_element: {graph_element}")

            # Ensure meta_dict is included, even if empty
            message_dict = record.to_dict()['message']
            message_dict['meta_dict'] = message_dict.get(
                'meta_dict', {}
            )  # Default to empty dict if None
            message_properties = flatten_dict(convert_enums(record.to_dict()))
            message_properties['embedding'] = self.embedding.embed(content)
            message_uuid = element_id

            try:
                self.storage.add_graph_elements(
                    [graph_element], include_source=True
                )
                self.storage.query(
                    "MERGE (m:Message {uuid: $uuid}) SET m += $props",
                    {"uuid": message_uuid, "props": message_properties},
                )
                for node in graph_element.nodes:
                    self.storage.query(
                        """
                        MATCH (m:Message {uuid: $message_uuid}), 
                        (n {id: $node_id})
                        MERGE (m)-[:CONTAINS]->(n)
                        """,
                        {"message_uuid": message_uuid, "node_id": node.id},
                    )
                logger.info(
                    f"""Message and entities for UUID 
                    {message_uuid} added successfully."""
                )
            except Exception as e:
                logger.error(f"Failed to add record: {e}")

    def delete_records(self, records: List[MemoryRecord]) -> None:
        r"""Deletes records from the graph database.

        Args:
            records (List[MemoryRecord]): List of memory records to delete.
        """
        for record in records:
            message_uuid = record.to_dict().get('uuid')
            if not message_uuid:
                logger.error("No UUID found in record, skipping deletion.")
                continue
            try:
                self.storage.query(
                    "MATCH (m:Message {uuid: $uuid}) DETACH DELETE m",
                    {"uuid": message_uuid},
                )
                logger.info(f"Deleted message with UUID {message_uuid}.")
            except Exception as e:
                logger.error(
                    f"Failed to delete record with UUID {message_uuid}: {e}"
                )

    def clear(self) -> None:
        r"""Clears all data from the graph database."""
        clear_query = "MATCH (n) DETACH DELETE n"
        self.storage.query(clear_query)
