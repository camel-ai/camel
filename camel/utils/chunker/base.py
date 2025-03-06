from abc import ABC, abstractmethod
from typing import List, Union
from unstructured.documents.elements import Element


class BaseChunker(ABC):
    r"""An abstract base class for all CAMEL chunkers."""

    @abstractmethod
    def chunk(
        self,
        content: Union[str, Element, List[Element]]
    ) -> List[Union[str, Element]]:
        r"""Chunk the given content"""
        pass