from typing import List, Union, IO, TYPE_CHECKING, Optional

from camel.loaders import UnstructuredIO
from camel.utils.chunker import BaseChunker
from unstructured.documents.elements import Element

class UioChunker(BaseChunker):
    def __init__(
        self,
        chunk_type: str = "chunk_by_title",
        max_characters: int = 500,
        metadata_filename: Optional[str] = None,
    ):
        self.uio = UnstructuredIO()
        self.chunk_type = chunk_type
        self.max_characters = max_characters
        self.metadata_filename = metadata_filename

    def chunk(self, text: List[Element]) -> List[Element]:
        return self.uio.chunk_elements(
            chunk_type=self.chunk_type,
            elements=text,
            max_characters=self.max_characters,
        )