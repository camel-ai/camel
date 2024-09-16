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

from abc import abstractmethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field

try:
    from unstructured.documents.elements import Element
except ImportError:
    Element = None


class Node(BaseModel):
    r"""Represents a node in a graph with associated properties.

    Attributes:
        id (Union[str, int]): A unique identifier for the node.
        type (str):  The type of the relationship.
        properties (dict): Additional properties and metadata associated with
            the node.
    """

    id: Union[str, int]
    type: str = "Node"
    properties: dict = Field(default_factory=dict)


class Relationship(BaseModel):
    r"""Represents a directed relationship between two nodes in a graph.

    Attributes:
        subj (Node): The subject/source node of the relationship.
        obj (Node): The object/target node of the relationship.
        type (str):  The type of the relationship.
        properties (dict): Additional properties associated with the
            relationship.
    """

    subj: Node
    obj: Node
    type: str = "Relationship"
    properties: dict = Field(default_factory=dict)


class GraphElement(BaseModel):
    r"""A graph element with lists of nodes and relationships.

    Attributes:
        nodes (List[Node]): A list of nodes in the graph.
        relationships (List[Relationship]): A list of relationships in the
            graph.
        source (Element): The element from which the graph information is
            derived.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    nodes: List[Node]
    relationships: List[Relationship]
    source: Element

    def __post_init__(self):
        if Element is None:
            raise ImportError("""The 'unstructured' package is required to use
                              the 'source' attribute.""")


class LabelledNode(BaseModel):
    """An entity in a graph."""

    label: str = Field(default="node", description="The label of the node.")
    embedding: Optional[List[float]] = Field(
        default=None, description="The embeddings of the node."
    )
    properties: Dict[str, Any] = Field(default_factory=dict)

    @abstractmethod
    def __str__(self) -> str:
        """Return the string representation of the node."""
        ...

    @property
    @abstractmethod
    def id(self) -> str:
        """Get the node id."""
        ...


class EntityNode(LabelledNode):
    """An entity in a graph."""

    name: str = Field(description="The name of the entity.")
    label: str = Field(default="entity", description="The label of the node.")
    properties: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        """Return the string representation of the node."""
        if self.properties:
            return f"{self.name} ({self.properties})"
        return self.name

    @property
    def id(self) -> str:
        """Get the node id."""
        return self.name.replace('"', " ")


class ChunkNode(LabelledNode):
    """A text chunk in a graph, to support vector search on node"""

    text: str = Field(description="The text content of the chunk.")
    id_: Optional[str] = Field(
        default=None,
        description="The id of the node. Defaults to a hash of the text.",
    )
    label: str = Field(
        default="text_chunk", description="The label of the node."
    )
    properties: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        """Return the string representation of the node."""
        return self.text

    @property
    def id(self) -> str:
        """Get the node id."""
        return str(hash(self.text)) if self.id_ is None else self.id_


class Relation(BaseModel):
    """A relation connecting two entities in a graph."""

    label: str
    source_id: str
    target_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        """Return the string representation of the relation."""
        if self.properties:
            return f"{self.label} ({self.properties})"
        return self.label

    @property
    def id(self) -> str:
        """Get the relation id."""
        return self.label


Triplet = Tuple[LabelledNode, Relation, LabelledNode]
