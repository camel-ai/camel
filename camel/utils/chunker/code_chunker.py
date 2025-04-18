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
import re
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from unstructured.documents.elements import Element

from camel.utils import get_model_encoding

from .base import BaseChunker


class CodeChunker(BaseChunker):
    r"""A class for chunking code or text while respecting structure
    and token limits.

    This class ensures that structured elements such as functions,
    classes, and regions are not arbitrarily split across chunks.
    It also handles oversized lines and Base64-encoded images.

    Attributes:
        chunk_size (int, optional): The maximum token size per chunk.
            (default: :obj:`8192`)
        remove_image: (bool, optional): If the chunker should skip the images.
        model_name (str, optional): The tokenizer model name used
            for token counting. (default: :obj:`"cl100k_base"`)
    """

    def __init__(
        self,
        chunk_size: int = 8192,
        model_name: str = "cl100k_base",
        remove_image: Optional[bool] = True,
    ):
        self.chunk_size = chunk_size
        self.tokenizer = get_model_encoding(model_name)
        self.remove_image = remove_image
        self.struct_pattern = re.compile(
            r'^\s*(?:(def|class|function)\s+\w+|'
            r'(public|private|protected)\s+[\w<>]+\s+\w+\s*\(|'
            r'\b(interface|enum|namespace)\s+\w+|'
            r'#\s*(region|endregion)\b)'
        )
        self.image_pattern = re.compile(
            r'!\[.*?\]\((?:data:image/[^;]+;base64,[a-zA-Z0-9+/]+=*|[^)]+)\)'
        )

    def count_tokens(self, text: str):
        r"""Counts the number of tokens in the given text.

        Args:
            text (str): The input text to be tokenized.

        Returns:
            int: The number of tokens in the input text.
        """
        return len(self.tokenizer.encode(text, disallowed_special=()))

    def _split_oversized(self, line: str) -> List[str]:
        r"""Splits an oversized line into multiple chunks based on token limits

        Args:
            line (str): The oversized line to be split.

        Returns:
            List[str]: A list of smaller chunks after splitting the
                oversized line.
        """
        tokens = self.tokenizer.encode(line, disallowed_special=())
        chunks = []
        buffer = []
        current_count = 0

        for token in tokens:
            buffer.append(token)
            current_count += 1

            if current_count >= self.chunk_size:
                chunks.append(self.tokenizer.decode(buffer).strip())
                buffer = []
                current_count = 0

        if buffer:
            chunks.append(self.tokenizer.decode(buffer))
        return chunks

    def chunk(self, content: List[str]) -> List["Element"]:
        r"""Splits the content into smaller chunks while preserving
        structure and adhering to token constraints.

        Args:
            content (List[str]): The content to be chunked.

        Returns:
            List[str]: A list of chunked text segments.
        """
        from unstructured.documents.elements import Element, ElementMetadata

        content_str = "\n".join(map(str, content))
        chunks = []
        current_chunk: list[str] = []
        current_tokens = 0
        struct_buffer: list[str] = []
        struct_tokens = 0

        for line in content_str.splitlines(keepends=True):
            if self.remove_image:
                if self.image_pattern.match(line):
                    continue

            line_tokens = self.count_tokens(line)

            if line_tokens > self.chunk_size:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                chunks.extend(self._split_oversized(line))
                continue

            if self.struct_pattern.match(line):
                if struct_buffer:
                    if current_tokens + struct_tokens <= self.chunk_size:
                        current_chunk.extend(struct_buffer)
                        current_tokens += struct_tokens
                    else:
                        if current_chunk:
                            chunks.append("".join(current_chunk))
                        current_chunk = struct_buffer.copy()
                        current_tokens = struct_tokens
                    struct_buffer = []
                    struct_tokens = 0

                struct_buffer.append(line)
                struct_tokens += line_tokens
            else:
                if struct_buffer:
                    struct_buffer.append(line)
                    struct_tokens += line_tokens
                else:
                    if current_tokens + line_tokens > self.chunk_size:
                        chunks.append("".join(current_chunk))
                        current_chunk = [line]
                        current_tokens = line_tokens
                    else:
                        current_chunk.append(line)
                        current_tokens += line_tokens

        if struct_buffer:
            if current_tokens + struct_tokens <= self.chunk_size:
                current_chunk.extend(struct_buffer)
            else:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                current_chunk = struct_buffer

        if current_chunk:
            chunks.append("".join(current_chunk))

        final_chunks = []
        for chunk in chunks:
            chunk_token = self.count_tokens(chunk)
            if chunk_token > self.chunk_size:
                final_chunks.extend(self._split_oversized(chunk))
            else:
                final_chunks.append(chunk)

        # TODO: need to reconsider how to correctly form metadata (maybe need
        # to decouple the connection with unstructuredIO)
        chunked_elements = []
        for chunk in final_chunks:
            element = Element(metadata=ElementMetadata())
            element.text = chunk
            chunked_elements.append(element)
        return chunked_elements
