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
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class NetworkXToolkit(BaseToolkit):
    _nx = None  # Class variable to store the networkx module

    @classmethod
    def _get_nx(cls):
        r"""Lazily import networkx module when needed."""
        if cls._nx is None:
            import networkx

            cls._nx = networkx
        return cls._nx

    def __init__(
        self,
        graph_type: Literal[
            'graph', 'digraph', 'multigraph', 'multidigraph'
        ] = 'graph',
    ):
        r"""Initializes the NetworkX graph client.

        Args:
            graph_type (Literal['graph', 'digraph', 'multigraph',
            'multidigraph']):
                Type of graph to create. Options are:
                - 'graph': Undirected graph
                - 'digraph': Directed graph
                - 'multigraph': Undirected graph with parallel edges
                - 'multidigraph': Directed graph with parallel edges
                (default: :obj:`'graph'`)
        """
        nx = self._get_nx()
        graph_types = {
            'graph': nx.Graph,
            'digraph': nx.DiGraph,
            'multigraph': nx.MultiGraph,
            'multidigraph': nx.MultiDiGraph,
        }
        graph_class = graph_types.get(graph_type.lower())
        if graph_class is None:
            raise ValueError(
                f"Invalid graph type: {graph_type}. Must be one "
                f"of: {list(graph_types.keys())}"
            )

        self.graph = graph_class()
        logger.info(f"Initialized NetworkX {graph_type} instance.")

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

    def get_shortest_path(
        self,
        source: str,
        target: str,
        weight: Optional[Union[str, Callable]] = None,
        method: Literal['dijkstra', 'bellman-ford'] = 'dijkstra',
    ) -> List[str]:
        r"""Finds the shortest path between two nodes.

        Args:
            source (str): The source node ID.
            target (str): The target node ID.
            weight (None, str or function, optional): Edge weights/distances.
                If None, every edge has weight/distance/cost 1.
                If string, use this edge attribute as the edge weight.
                If function, the weight of an edge is the value returned by
                the function. The function must accept three positional
                arguments: the two endpoints and the edge attribute
                dictionary. (default: :obj:`None`)
            method (Literal['dijkstra', 'bellman-ford'], optional): Algorithm
                to compute the path. Ignored if weight is None. (default:
                :obj:`'dijkstra'`)

        Returns:
            List[str]: A list of nodes in the shortest path.
        """
        logger.info(
            f"Finding shortest path from '{source}' to '{target}' "
            f"using {method} algorithm"
        )
        try:
            nx = self._get_nx()
            path = nx.shortest_path(
                self.graph,
                source=source,
                target=target,
                weight=weight,
                method=method,
            )
            logger.debug(f"Found path: {' -> '.join(path)}")
            return path
        except nx.NetworkXNoPath:
            error_msg = f"No path exists between '{source}' and '{target}'"
            logger.error(error_msg)
            return [error_msg]
        except nx.NodeNotFound as e:
            error_msg = f"Node not found in graph: {e!s}"
            logger.error(error_msg)
            return [error_msg]

    def compute_centrality(self) -> Dict[str, float]:
        r"""Computes centrality measures for the graph.

        Returns:
            Dict[str, float]: Centrality values for each node.
        """
        logger.info("Computing centrality measures.")
        nx = self._get_nx()
        return nx.degree_centrality(self.graph)

    def serialize_graph(self) -> str:
        r"""Serializes the graph to a JSON string.

        Returns:
            str: The serialized graph in JSON format.
        """
        logger.info("Serializing the graph.")
        nx = self._get_nx()
        return json.dumps(nx.node_link_data(self.graph), ensure_ascii=False)

    def deserialize_graph(self, data: str) -> None:
        r"""Loads a graph from a serialized JSON string.

        Args:
            data (str): The JSON string representing the graph.
        """
        logger.info("Deserializing graph from JSON data.")
        nx = self._get_nx()
        self.graph = nx.node_link_graph(json.loads(data))

    def export_to_file(self, file_path: str) -> None:
        r"""Exports the graph to a file in JSON format.

        Args:
            file_path (str): The file path to save the graph.
        """
        logger.info(f"Exporting graph to file: {file_path}")
        nx = self._get_nx()
        with open(file_path, "w") as file:
            json.dump(nx.node_link_data(self.graph), file, ensure_ascii=False)

    def import_from_file(self, file_path: str) -> None:
        r"""Imports a graph from a JSON file.

        Args:
            file_path (str): The file path to load the graph from.
        """
        logger.info(f"Importing graph from file: {file_path}")
        nx = self._get_nx()
        with open(file_path, "r") as file:
            self.graph = nx.node_link_graph(json.load(file))

    def clear_graph(self) -> None:
        r"""Clears the current graph."""
        logger.info("Clearing the graph.")
        self.graph.clear()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for the
                toolkit methods.
        """
        return [
            FunctionTool(self.add_edge),
            FunctionTool(self.add_node),
            FunctionTool(self.clear_graph),
            FunctionTool(self.compute_centrality),
            FunctionTool(self.deserialize_graph),
            FunctionTool(self.export_to_file),
            FunctionTool(self.get_edges),
            FunctionTool(self.get_nodes),
            FunctionTool(self.import_from_file),
            FunctionTool(self.serialize_graph),
            FunctionTool(self.get_shortest_path),
        ]
