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

import json
import logging
from typing import Any, Dict, List, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


class NetworkXGraph:
    def __init__(self):
        r"""Initializes the NetworkXGraph client."""
        self.graph = nx.Graph()
        logger.info("Initialized NetworkXGraph instance.")

    def add_node(self, node_id: str, **attributes: Any) -> None:
        r"""Adds a node to the graph.

        Args:
            node_id (str): The ID of the node.
            attributes (dict): Additional node attributes.
        """
        logger.info(f"Adding node: {node_id}, attributes: {attributes}")
        self.graph.add_node(node_id, **attributes)

    def add_edge(self, source: str, target: str, **attributes: Any) -> None:
        r"""Adds an edge to the graph.

        Args:
            source (str): Source node ID.
            target (str): Target node ID.
            attributes (dict): Additional edge attributes.
        """
        logger.info(
            f"Adding edge: {source} -> {target}, attributes: {attributes}"
        )
        self.graph.add_edge(source, target, **attributes)

    def get_nodes(self) -> List[str]:
        r"""Returns all nodes in the graph.

        Returns:
            List[str]: A list of node IDs.
        """
        logger.info("Fetching all nodes.")
        return list(self.graph.nodes)

    def get_edges(self) -> List[Tuple[str, str]]:
        r"""Returns all edges in the graph.

        Returns:
            List[Tuple[str, str]]: A list of edges as (source, target).
        """
        logger.info("Fetching all edges.")
        return list(self.graph.edges)

    def get_shortest_path(self, source: str, target: str) -> List[str]:
        r"""Finds the shortest path between two nodes.

        Args:
            source (str): The source node ID.
            target (str): The target node ID.

        Returns:
            List[str]: A list of nodes in the shortest path.
        """
        logger.info(f"Finding shortest path from {source} to {target}.")
        try:
            path = nx.shortest_path(self.graph, source=source, target=target)
            return path
        except nx.NetworkXNoPath as e:
            logger.error(f"No path exists between {source} and {target}: {e}")
            return []
        except nx.NodeNotFound as e:
            logger.error(f"Node not found in the graph: {e}")
            return []

    def compute_centrality(self) -> Dict[str, float]:
        r"""Computes centrality measures for the graph.

        Returns:
            Dict[str, float]: Centrality values for each node.
        """
        logger.info("Computing centrality measures.")
        return nx.degree_centrality(self.graph)

    def serialize_graph(self) -> str:
        r"""Serializes the graph to a JSON string.

        Returns:
            str: The serialized graph in JSON format.
        """
        logger.info("Serializing the graph.")
        return json.dumps(nx.node_link_data(self.graph))

    def deserialize_graph(self, data: str) -> None:
        r"""Loads a graph from a serialized JSON string.

        Args:
            data (str): The JSON string representing the graph.
        """
        logger.info("Deserializing graph from JSON data.")
        self.graph = nx.node_link_graph(json.loads(data))

    def export_to_file(self, file_path: str) -> None:
        r"""Exports the graph to a file in JSON format.

        Args:
            file_path (str): The file path to save the graph.
        """
        logger.info(f"Exporting graph to file: {file_path}")
        with open(file_path, "w") as file:
            json.dump(nx.node_link_data(self.graph), file)

    def import_from_file(self, file_path: str) -> None:
        r"""Imports a graph from a JSON file.

        Args:
            file_path (str): The file path to load the graph from.
        """
        logger.info(f"Importing graph from file: {file_path}")
        with open(file_path, "r") as file:
            self.graph = nx.node_link_graph(json.load(file))

    def clear_graph(self) -> None:
        r"""Clears the current graph."""
        logger.info("Clearing the graph.")
        self.graph.clear()
