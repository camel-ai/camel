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

import json
import logging
from typing import Any, Dict, List, Optional

from camel.embeddings import BaseEmbedding, OpenAIEmbedding
from camel.memories.base import MemoryBlock
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.graph_storages import BaseGraphStorage, Neo4jGraph

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
        self.storage = storage or self.default_graph_storage(
            url, username, password, database
        )

    def default_graph_storage(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = "neo4j",
    ) -> BaseGraphStorage:
        if (
            url is None
            or username is None
            or password is None
            or database is None
        ):
            raise ValueError(
                "url, username, password, and database must all be provided"
                "and non-None"
            )

        return Neo4jGraph(url, username, password, database)

    def retrieve(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[ContextRecord]:
        r"""Retrieves records from the graph database based on a query.

        Args:
            query (str): The query string to execute.
            params (Optional[Dict[str, Any]]): Parameters for the query.

        Returns:
            List[ContextRecord]: A list of context records retrieved from the
                graph database.
        """
        try:
            results = self.storage.query(query, params)
            scores = self._calculate_scores(query, results)
            return [
                ContextRecord(
                    memory_record=MemoryRecord.from_dict(result), score=score
                )
                for result, score in zip(results, scores)
            ]
        except Exception as e:
            logger.error(f"Error retrieving records: {e}")
            return []

    def write_records(self, records: List[MemoryRecord]) -> None:
        """Writes records to the graph database."""
        for record in records:
            content = record.message.content

            if not isinstance(content, str):
                logger.error(
                    "Expected content to be a string,"
                    f"got {type(content)}: {content}"
                )
                continue

            try:
                data = json.loads(content)
                subj = data.get("subject")
                obj = data.get("object")
                rel = data.get("relation")
            except json.JSONDecodeError:
                logger.error(f"Error parsing content as JSON: {content}")
                continue

            if subj and obj and rel:
                self.storage.add_triplet(subj, obj, rel)

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
                data = json.loads(content)
                subj = data.get("subject")
                obj = data.get("object")
                rel = data.get("relation")
            except json.JSONDecodeError:
                logger.error(f"Error parsing content as JSON: {content}")
                continue

            if subj and obj and rel:
                self.storage.delete_triplet(subj, obj, rel)

    def _calculate_scores(self, query: str, results: List[Any]) -> List[float]:
        query_vector = self.embedding.embed(query)
        scores = []
        for result in results:
            result_text = result.get("content", "")
            result_vector = self.embedding.embed(result_text)
            score = self._cosine_similarity(query_vector, result_vector)
            scores.append(score)
        return scores

    def _cosine_similarity(
        self, vec1: List[float], vec2: List[float]
    ) -> float:
        # Calculate cosine similarity between two vectors
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = sum(a * a for a in vec1) ** 0.5
        norm_b = sum(b * b for b in vec2) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def clear(self) -> None:
        """Clears all data from the graph database."""
        if self.storage:
            self.storage.clear()
        else:
            print("Warning: No storage to clear.")
