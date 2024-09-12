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
from enum import Enum
from typing import List, Optional

from camel.embeddings import BaseEmbedding, OpenAIEmbedding
from camel.memories.base import MemoryBlock
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.graph_storages import BaseGraphStorage, Neo4jGraph
from camel.types import OpenAIBackendRole, RoleType

logger = logging.getLogger(__name__)


class GraphDBBlock(MemoryBlock):
    r"""An implementation of the MemoryBlock abstract base class for
    maintaining and retrieving information using a graph database.

    Args:
        storage (Optional[BaseGraphStorage], optional): The storage mechanism
            for the graph database. Defaults to a specific implementation
            if not provided. (default: None)
        embedding (Optional[BaseEmbedding], optional): Embedding mechanism
            toconvert text into vector representations. Defaults to
            OpenAIEmbedding if not provided. (default: None)
    """

    def __init__(
        self,
        storage: Optional[BaseGraphStorage] = None,
        embedding: Optional[BaseEmbedding] = None,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = "neo4j",
    ) -> None:
        self.embedding = embedding or OpenAIEmbedding()
        self.storage = storage or Neo4jGraph(url, username, password, database)

    def retrieve(
        self,
        query_embedding: Optional[List[float]] = None,
        limit: int = 25,
    ) -> List[ContextRecord]:
        r"""Retrieves records from the graph database based on query embedding.

        Args:
            query_embedding (Optional[List[float]]): The embedding vector
                for similarity search.
            limit (int): The maximum number of records to retrieve.
                Defaults to 10.
            order_by (str): The property to order by in the default query.
                Defaults to "timestamp".
            desc (bool): Whether to order in descending order.
                Defaults to True.

        Returns:
            List[ContextRecord]: A list of context records retrieved
                from the graph database.
        """
        try:
            if query_embedding:
                # Perform a similarity search based on the provided embedding
                results = self.storage.query(
                    """
                    MATCH (n:Message)
                    WHERE exists(n.embedding)
                    WITH n, gds.similarity.cosine(
                        n.embedding, $query_embedding
                    ) AS similarity
                    RETURN n, similarity
                    ORDER BY similarity DESC
                    LIMIT $limit
                    """,
                    {"query_embedding": query_embedding, "limit": limit},
                )
            else:
                # Default retrieval logic when no query embedding is provided
                results = self.storage.query(
                    """
                    MATCH (n:Message)
                    RETURN n
                    LIMIT $limit
                    """,
                    {"limit": limit},
                )

            def reconstruct_from_flat(d):
                # Reconstruct message object and handle Enum conversions
                reconstructed = {}
                message = {}
                for key, value in d.items():
                    if key == 'embedding':
                        continue  # Skip the embedding property
                    if value == '__none__':
                        value = None  # Convert back to None
                    if value == '__empty_dict__':
                        value = {}  # Convert back to an empty dictionary
                    if key == 'role_at_backend':
                        value = OpenAIBackendRole[value]

                    # Handle only message-related keys
                    if key.startswith('message_'):
                        sub_key = key[len('message_') :]
                        if sub_key == 'role_type':
                            value = RoleType[
                                value
                            ]  # Convert back to Enum if applicable
                        message[sub_key] = value
                    else:
                        reconstructed[key] = value

                reconstructed['message'] = message
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
        """Writes recordes to the graph database."""
        for record in records:
            properties = record.to_dict()

            def flatten_and_convert(d):
                for key, value in list(d.items()):
                    if isinstance(value, Enum):
                        d[key] = value.name  # Convert Enum to its name
                    elif value is None:
                        d[key] = (
                            '__none__'  # Convert None to a sentinel string
                        )
                    elif isinstance(value, dict):
                        if value:  # If dictionary is not empty
                            for sub_key, sub_value in flatten_and_convert(
                                value
                            ).items():
                                d[f"{key}_{sub_key}"] = sub_value
                            del d[key]
                        else:
                            d[key] = '__empty_dict__'
                    elif isinstance(value, list):
                        d[key] = [
                            str(i)
                            if not isinstance(i, (str, int, float, bool))
                            else i
                            for i in value
                        ]
                    else:
                        d[key] = (
                            str(value)
                            if not isinstance(value, (str, int, float, bool))
                            else value
                        )
                return d

            properties = flatten_and_convert(properties)

            content = record.message.content

            if not isinstance(content, str):
                logger.error(
                    "Expected content to be a string, got"
                    f" {type(content)}: {content}"
                )
                continue

            embedding = self.embedding.embed(content)
            properties['embedding'] = embedding

            try:
                self.storage.add_node(label="Message", properties=properties)
                logger.info("Node with label 'Message' added successfully.")
            except Exception as e:
                logger.error(f"Failed to add node with label 'Message': {e!s}")

    def delete_records(self, records: List[MemoryRecord]) -> None:
        """Deletes records to the graph database."""
        for record in records:
            content = record.message.content

            if not isinstance(content, str):
                logger.error(
                    "Expected content to be a string,"
                    f"got {type(content)}: {content}"
                )
                continue

            try:
                # Assume that record deletion involves removing
                # nodes and relationships
                self.storage.delete_triplet(
                    subj=content, obj=content, rel="NEXT"
                )
            except Exception as e:
                logger.error(f"Failed to delete record: {e!s}")

    def clear(self) -> None:
        """Clears all data from the graph database."""
        if self.storage:
            self.storage.clear()
        else:
            print("Warning: No storage to clear.")
