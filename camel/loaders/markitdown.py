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
import os
from typing import Dict, List, Optional

from markitdown import MarkItDown


class MarkItDownConverter:
    r"""
    MarkitDown convert various file types into Markdown format.

    Supported Input Formats:
        - PDF
        - Microsoft Office documents:
            - Word (.doc, .docx)
            - Excel (.xls, .xlsx)
            - PowerPoint (.ppt, .pptx)
        - EPUB
        - HTML
        - Images (with EXIF metadata and OCR support)
        - Audio files (with EXIF metadata and speech transcription)
        - Text-based formats:
            - CSV
            - JSON
            - XML
        - ZIP archives (iterates over contents)
        - YouTube URLs (via transcript extraction)
    """

    def __init__(
        self,
        llm_client: Optional[object] = None,
        llm_model: Optional[str] = None,
    ):
        r"""
        Initializes the Converter.

        Args:
            llm_client (Optional[object]): Optional client for LLM integration.
            llm_model (Optional[str]): Optional model name for the LLM.
        """
        self.converter = MarkItDown(llm_client=llm_client, llm_model=llm_model)

    def convert_file(self, file_path: str) -> str:
        r"""
        Converts the given file to Markdown format.

        Args:
            file_path (str): Path to the input file.

        Returns:
            str: Converted Markdown text.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            Exception: For other errors during conversion.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            result = self.converter.convert(file_path)
            return result.text_content
        except Exception as e:
            raise Exception(f"Error converting file '{file_path}': {e}")

    def convert_files(self, file_paths: List[str]) -> Dict[str, str]:
        r"""
        Converts multiple files to Markdown format.

        Args:
            file_paths (List[str]): List of file paths to convert.

        Returns:
            Dict[str, str]: Dictionary mapping file paths to their
            converted Markdown text.

        Raises:
            Exception: For errors during conversion of any file.
        """
        converted_files = {}
        for path in file_paths:
            try:
                converted_files[path] = self.convert_file(path)
            except Exception as e:
                converted_files[path] = f"Error: {e}"
        return converted_files
