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
import unittest

from camel.toolkits import NetworkXToolkit


class TestNetworkXToolkit(unittest.TestCase):
    def setUp(self):
        self.graph = NetworkXToolkit()

    def test_add_node(self):
        self.graph.add_node("A", attr1="value1")
        nodes = self.graph.get_nodes()
        self.assertIn("A", nodes)

    def test_add_edge(self):
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_edge("A", "B", weight=2)
        edges = self.graph.get_edges()
        self.assertIn(("A", "B"), edges)

    def test_get_nodes(self):
        self.graph.add_node("A")
        self.graph.add_node("B")
        nodes = self.graph.get_nodes()
        self.assertListEqual(nodes, ["A", "B"])

    def test_get_edges(self):
        self.graph.add_node("A")
        self.graph.add_node("B")
        self.graph.add_edge("A", "B")
        edges = self.graph.get_edges()
        self.assertListEqual(edges, [("A", "B")])

    def test_shortest_path(self):
        self.graph.add_edge("A", "B")
        self.graph.add_edge("B", "C")
        path = self.graph.get_shortest_path("A", "C")
        self.assertListEqual(path, ["A", "B", "C"])

    def test_shortest_path_no_path(self):
        self.graph.add_node("A")
        self.graph.add_node("C")
        path = self.graph.get_shortest_path("A", "C")
        self.assertListEqual(path, ["No path exists between 'A' and 'C'"])

    def test_compute_centrality(self):
        self.graph.add_edge("A", "B")
        self.graph.add_edge("B", "C")
        centrality = self.graph.compute_centrality()
        expected_centrality = {"A": 0.5, "B": 1.0, "C": 0.5}
        self.assertEqual(centrality, expected_centrality)

    def test_serialize_graph(self):
        self.graph.add_edge("A", "B")
        serialized = self.graph.serialize_graph()
        self.assertIsInstance(serialized, str)

    def test_deserialize_graph(self):
        data = """{"directed": false, "multigraph": false, "graph": {},
         "nodes": [{"id": "A"}, {"id": "B"}],
          "links": [{"source": "A", "target": "B"}]}"""
        self.graph.deserialize_graph(data)
        nodes = self.graph.get_nodes()
        edges = self.graph.get_edges()
        self.assertListEqual(nodes, ["A", "B"])
        self.assertListEqual(edges, [("A", "B")])

    def test_export_import_file(self):
        file_path = "test_graph.json"
        self.graph.add_edge("A", "B")
        self.graph.export_to_file(file_path)

        new_graph = NetworkXToolkit()
        new_graph.import_from_file(file_path)
        self.assertListEqual(new_graph.get_nodes(), ["A", "B"])
        self.assertListEqual(new_graph.get_edges(), [("A", "B")])

    def test_clear_graph(self):
        self.graph.add_edge("A", "B")
        self.graph.clear_graph()
        self.assertListEqual(self.graph.get_nodes(), [])
        self.assertListEqual(self.graph.get_edges(), [])


if __name__ == "__main__":
    unittest.main()
