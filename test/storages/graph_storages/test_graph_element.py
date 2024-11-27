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


import pytest
from unstructured.documents.elements import Element

from camel.loaders import UnstructuredIO
from camel.storages.graph_storages.graph_element import (
    GraphElement,
    Node,
    Relationship,
)

sample_element = UnstructuredIO().create_element_from_text("sample text")


@pytest.fixture
def sample_nodes():
    return [
        Node(id=1, type="Person", properties={"name": "Alice"}),
        Node(id=2, type="Person", properties={"name": "Bob"}),
    ]


@pytest.fixture
def sample_relationship(sample_nodes):
    return Relationship(
        subj=sample_nodes[0],
        obj=sample_nodes[1],
        type="Friend",
        properties={"since": "2020"},
    )


@pytest.fixture
def sample_graph_element(sample_nodes, sample_relationship):
    return GraphElement(
        nodes=sample_nodes,
        relationships=[sample_relationship],
        source=sample_element,
    )


def test_graph_element_initialization(sample_nodes, sample_relationship):
    graph_element = GraphElement(
        nodes=sample_nodes,
        relationships=[sample_relationship],
        source=sample_element,
    )
    assert len(graph_element.nodes) == 2
    assert len(graph_element.relationships) == 1
    assert isinstance(graph_element.source, Element)


def test_graph_element_empty_nodes_relationships():
    graph_element = GraphElement(
        nodes=[],
        relationships=[],
        source=sample_element,
    )
    assert graph_element.nodes == []
    assert graph_element.relationships == []
