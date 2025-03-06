from typing import List, Union, IO, TYPE_CHECKING, Optional

from camel.loaders import UnstructuredIO
from camel.utils.chunker import BaseChunker
from unstructured.documents.elements import Element

class UioChunker(BaseChunker):
    r"""A class for chunking text while respecting structure and
    character limits.

    This class ensures that structured elements, such as document sections
    and titles, are not arbitrarily split across chunks. It utilizes the
    `UnstructuredIO` class to process and segment elements while maintaining
    readability and coherence. The chunking method can be adjusted based on
    the provided `chunk_type` parameter.

    Args:
        chunk_type (str, optional): The method used for chunking text.
            (default: :obj:`"chunk_by_title"`)
        max_characters (int, optional): The maximum number of characters
            allowed per chunk. (default: :obj:`500`)
        metadata_filename (Optional[str], optional): An optional filename
            for storing metadata related to chunking. (default: :obj:`None`)
    """
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

    def chunk(self, content: List[Element]) -> List[Element]:
        r"""Splits the content into smaller chunks while preserving
        structure and adhering to token constraints.

        Args:
            content (List[Element]): The content to be chunked.

        Returns:
            List[Element]: A list of chunked text segments.
        """
        return self.uio.chunk_elements(
            chunk_type=self.chunk_type,
            elements=content,
            max_characters=self.max_characters,
        )