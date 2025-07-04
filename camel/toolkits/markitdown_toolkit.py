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

from typing import Dict, List, Optional

from camel.loaders.markitdown import MarkItDownLoader
from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class MarkItDownToolkit(BaseToolkit):
    r"""A class representing a toolkit for MarkItDown."""

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)

    def load_files(self, file_paths: List[str]) -> Dict[str, str]:
        r"""Scrapes content from a list of files and converts it to Markdown.

        This function takes a list of local file paths, attempts to convert
        each file into Markdown format, and returns the converted content.
        The conversion is performed in parallel for efficiency.

        Supported file formats include:
        - PDF (.pdf)
        - Microsoft Office: Word (.doc, .docx), Excel (.xls, .xlsx),
          PowerPoint (.ppt, .pptx)
        - EPUB (.epub)
        - HTML (.html, .htm)
        - Images (.jpg, .jpeg, .png) for OCR
        - Audio (.mp3, .wav) for transcription
        - Text-based formats (.csv, .json, .xml, .txt)
        - ZIP archives (.zip)

        Args:
            file_paths (List[str]): A list of local file paths to be
                converted.

        Returns:
            Dict[str, str]: A dictionary where keys are the input file paths
                and values are the corresponding content in Markdown format.
                If conversion of a file fails, the value will contain an
                error message.
        """
        return MarkItDownLoader().convert_files(
            file_paths=file_paths, parallel=True
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.load_files),
        ]
