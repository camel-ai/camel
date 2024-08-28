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
import os
from typing import Any, Dict, List, Optional

import nltk
from networkx import Graph

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
    """

    def __init__(
        self,
        storage: Optional[BaseGraphStorage] = None,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = "neo4j",
    ) -> None:
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
        # Try to get details from environment variables first
        url = os.getenv('NEO4J_URI', url)
        username = os.getenv('NEO4J_USERNAME', username)
        password = os.getenv('NEO4J_PASSWORD', password)
        database = os.getenv('NEO4J_DATABASE', database)

        # Log an error if any of the necessary values are missing
        if not url or not username or not password:
            logger.error(
                "Neo4j connection detailed are missing."
                "Ensure environment variables or parameters are set for"
                "NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
            )
            raise ValueError("Missing Neo4j connection details.")

        # Create and return an instance of Neo4jGraph
        return Neo4jGraph(url, username, password, database or "neo4j")

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

            if isinstance(content, str):
                try:
                    data = json.loads(content)
                    subj = data.get('subject')
                    obj = data.get('object')
                    rel = data.get('relation')
                except json.JSONDecodeError:
                    logger.error(f"Error parsing content as JSON: {content}")
                    continue
            else:
                subj = content.get('subject')
                obj = content.get('object')
                rel = content.get('relation')

            if subj and obj and rel:
                self.write_triplet(subj, obj, rel)

    def write_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Writes a triplet to the graph database.

        Args:
            subj (str): The subject of the triplet.
            obj (str): The object of the triplet.
            rel (str): The relationship between subject and object.
        """
        self.storage.add_triplet(subj, obj, rel)

    def delete_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Deletes a triplet from the graph database.

        Args:
            subj (str): The subject of the triplet.
            obj (str): The object of the triplet.
            rel (str): The relationship between subject and object.
        """
        self.storage.delete_triplet(subj, obj, rel)

    def _calculate_scores(self, query: str, results: List[Any]) -> List[float]:
        query_graph = self._build_graph(query)
        scores = []
        for result in results:
            result_graph = self._build_graph(result)
            score = self._graph_similarity(query_graph, result_graph)
            scores.append(score)
        return scores

    def _build_graph(self, text: str) -> Graph:
        # Tokenize the text and create a graph
        tokens = nltk.word_tokenize(text)
        graph: Graph = Graph()
        for token in tokens:
            graph.add_node(token)
        for i in range(len(tokens) - 1):
            graph.add_edge(tokens[i], tokens[i + 1])
        return graph

    def _graph_similarity(self, graph1: Graph, graph2: Graph) -> float:
        # Calculate the similarity between two graphs
        #  using the Jaccard similarity
        intersection = set(graph1.nodes) & set(graph2.nodes)
        union = set(graph1.nodes) | set(graph2.nodes)
        return len(intersection) / len(union)

    def clear(self) -> None:
        """Clears all data from the graph database."""
        if self.storage:
            self.storage.clear()
        else:
            print("Warning: No storage to clear.")
