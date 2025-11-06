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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import ClassVar, Dict, List, Optional

from camel.logger import get_logger

logger = get_logger(__name__)


class MarkItDownLoader:
    r"""MarkitDown convert various file types into Markdown format.

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

    SUPPORTED_FORMATS: ClassVar[List[str]] = [
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".epub",
        ".html",
        ".htm",
        ".jpg",
        ".jpeg",
        ".png",
        ".mp3",
        ".wav",
        ".csv",
        ".json",
        ".xml",
        ".zip",
        ".txt",
    ]

    def __init__(
        self,
        llm_client: Optional[object] = None,
        llm_model: Optional[str] = None,
    ):
        r"""Initializes the Converter.

        Args:
            llm_client (Optional[object]): Optional client for LLM integration.
                (default: :obj:`None`)
            llm_model (Optional[str]): Optional model name for the LLM.
                (default: :obj:`None`)
        """
        from markitdown import MarkItDown

        try:
            self.converter = MarkItDown(
                llm_client=llm_client, llm_model=llm_model
            )
            logger.info("MarkItDownLoader initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MarkItDown Converter: {e}")
            raise Exception(f"Failed to initialize MarkItDown Converter: {e}")

    def _validate_format(self, file_path: str) -> bool:
        r"""Validates if the file format is supported.

        Args:
            file_path (str): Path to the input file.

        Returns:
            bool: True if the format is supported, False otherwise.
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.SUPPORTED_FORMATS

    def convert_file(self, file_path: str) -> str:
        r"""Converts the given file to Markdown format.

        Args:
            file_path (str): Path to the input file.

        Returns:
            str: Converted Markdown text.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is not supported.
            Exception: For other errors during conversion.
        """
        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self._validate_format(file_path):
            logger.error(
                f"Unsupported file format: {file_path}."
                f"Supported formats are "
                f"{MarkItDownLoader.SUPPORTED_FORMATS}"
            )
            raise ValueError(f"Unsupported file format: {file_path}")

        try:
            logger.info(f"Converting file: {file_path}")
            result = self.converter.convert(file_path)
            logger.info(f"File converted successfully: {file_path}")
            return result.text_content
        except Exception as e:
            logger.error(f"Error converting file '{file_path}': {e}")
            raise Exception(f"Error converting file '{file_path}': {e}")

    def convert_files(
        self,
        file_paths: List[str],
        parallel: bool = False,
        skip_failed: bool = False,
    ) -> Dict[str, str]:
        r"""Converts multiple files to Markdown format.

        Args:
            file_paths (List[str]): List of file paths to convert.
            parallel (bool): Whether to process files in parallel.
                (default: :obj:`False`)
            skip_failed (bool): Whether to skip failed files instead
                of including error messages.
                (default: :obj:`False`)

        Returns:
            Dict[str, str]: Dictionary mapping file paths to their
                converted Markdown text.

        Raises:
            Exception: For errors during conversion of any file if
                skip_failed is False.
        """
        from tqdm.auto import tqdm

        converted_files = {}

        if parallel:
            with ThreadPoolExecutor() as executor:
                future_to_path = {
                    executor.submit(self.convert_file, path): path
                    for path in file_paths
                }
                for future in tqdm(
                    as_completed(future_to_path),
                    total=len(file_paths),
                    desc="Converting files (parallel)",
                ):
                    path = future_to_path[future]
                    try:
                        converted_files[path] = future.result()
                    except Exception as e:
                        if skip_failed:
                            logger.warning(
                                f"Skipping file '{path}' due to error: {e}"
                            )
                        else:
                            logger.error(
                                f"Error processing file '{path}': {e}"
                            )
                            converted_files[path] = f"Error: {e}"
        else:
            for path in tqdm(file_paths, desc="Converting files (sequential)"):
                try:
                    logger.info(f"Processing file: {path}")
                    converted_files[path] = self.convert_file(path)
                except Exception as e:
                    if skip_failed:
                        logger.warning(
                            f"Skipping file '{path}' due to error: {e}"
                        )
                    else:
                        logger.error(f"Error processing file '{path}': {e}")
                        converted_files[path] = f"Error: {e}"

        return converted_files
