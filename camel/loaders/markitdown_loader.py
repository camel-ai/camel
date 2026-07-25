# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union

from camel.loaders.base_loader import BaseLoader
from camel.logger import get_logger

logger = get_logger(__name__)


class MarkItDownLoader(BaseLoader):
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
        ".md",
    ]

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        llm_client: Optional[object] = None,
        llm_model: Optional[str] = None,
    ):
        if config:
            llm_client = config.get('llm_client', llm_client)
            llm_model = config.get('llm_model', llm_model)

        super().__init__(config=config)

        from markitdown import MarkItDown

        try:
            self.converter = MarkItDown(
                llm_client=llm_client, llm_model=llm_model
            )
            logger.info("MarkItDownLoader initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MarkItDown Converter: {e}")
            raise Exception(f"Failed to initialize MarkItDown Converter: {e}")

    @property
    def supported_formats(self) -> set[str]:
        return set(self.SUPPORTED_FORMATS)

    def _load_single(
        self, source: Union[str, Path], **kwargs: Any
    ) -> Dict[str, Any]:
        file_path = str(source)
        response = self.convert_file(file_path)
        return {"content": response, "source": file_path}

    def _validate_format(self, file_path: str) -> bool:
        r"""Validates if the file format is supported."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.SUPPORTED_FORMATS

    def convert_file(self, file_path: str) -> str:
        r"""Converts the given file to Markdown format."""
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
        r"""Converts multiple files to Markdown format."""
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
