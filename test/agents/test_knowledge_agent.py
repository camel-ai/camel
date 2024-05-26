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
from unittest.mock import Mock

from camel.agents import KnowledgeGraphAgent
from camel.storages.graph_storages.graph_element import Node, Relationship

agent = KnowledgeGraphAgent()


def test_validate_node_valid():
    valid_node = Node(id='test_id', type='test_type', properties={})
    assert agent._validate_node(valid_node)


def test_validate_node_invalid():
    invalid_node = "not a Node object"
    assert not agent._validate_node(invalid_node)


def test_validate_relationship_valid():
    valid_relationship = Relationship(
        Node(id='subj_id', type='subj_type', properties={}),
        Node(id='obj_id', type='obj_type', properties={}),
        'test_type',
        {},
    )
    assert agent._validate_relationship(valid_relationship)


def test_validate_relationship_invalid():
    invalid_relationship = "not a Relationship object"
    assert not agent._validate_relationship(invalid_relationship)


def test_parse_graph_elements():
    agent.element = Mock()
    input_string = """
    Node(id='node_id', type='node_type', properties={})
    Relationship(subj=Node(id='subj_id', type='subj_type', properties={}), obj=Node(id='obj_id', type='obj_type', properties={}), type='test_type', properties={})
    """
    expected_nodes = [
        Node(id='node_id', type='node_type', properties={}),
        Node(id='subj_id', type='subj_type', properties={}),
        Node(id='obj_id', type='obj_type', properties={}),
    ]

    result = agent._parse_graph_elements(input_string)
    assert result.nodes == expected_nodes
