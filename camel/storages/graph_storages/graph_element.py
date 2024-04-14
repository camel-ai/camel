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
from __future__ import annotations

from typing import Any, List, Union

from pydantic import BaseModel, Field


class Node(BaseModel):
    r"""Represents a node in a graph with associated properties.

    Args:
        id (Union[str, int]): A unique identifier for the node.
        type (str): The type or label of the node, default is "Node".
        properties (dict): Additional properties and metadata associated with
            the node.
    """
    id: Union[str, int]
    type: str = "Node"
    properties: dict = Field(default_factory=dict)


class Relationship(BaseModel):
    r"""Represents a directed relationship between two nodes in a graph.

    Args:
        source (Node): The source node of the relationship.
        target (Node): The target node of the relationship.
        type (str): The type of the relationship.
        properties (dict): Additional properties associated with the
            relationship.
    """
    source: Node
    target: Node
    type: str
    properties: dict = Field(default_factory=dict)


class BaseModelConfig:
    arbitrary_types_allowed = True


class GraphElement(BaseModel):

    class Config(BaseModelConfig):
        pass

    nodes: List[Node]
    relationships: List[Relationship]
    source: Any
