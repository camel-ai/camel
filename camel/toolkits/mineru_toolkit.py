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

from camel.loaders.mineru_extractor import MinerU
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import api_keys_required


class MinerUToolkit(BaseToolkit):
    r"""Toolkit for extracting and processing document content
        using MinerU API.

    Provides comprehensive document processing capabilities including content
    extraction from URLs and files, with support for OCR, formula recognition,
    and table detection through the MinerU API service.

    Note:
        - Maximum file size: 200MB per file
        - Maximum pages: 600 pages per file
        - Daily quota: 2000 pages for high-priority parsing
        - Network restrictions may affect certain URLs (e.g., GitHub, AWS)
    """

    @api_keys_required(
        [
            (None, "MINERU_API_KEY"),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = "https://mineru.net/api/v4",
        is_ocr: bool = False,
        enable_formula: bool = False,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "en",
        wait: bool = True,
        timeout: float = 300,
    ) -> None:
        r"""Initialize the MinerU document processing toolkit.

        Args:
            api_key (Optional[str]): Authentication key for MinerU API access.
                If not provided, uses MINERU_API_KEY environment variable.
                (default: :obj:`None`)
            api_url (Optional[str]): Base endpoint URL for MinerU API service.
                (default: :obj:`"https://mineru.net/api/v4"`)
            is_ocr (bool): Enable Optical Character Recognition for image-based
                text extraction. (default: :obj:`False`)
            enable_formula (bool): Enable mathematical formula detection and
                recognition. (default: :obj:`False`)
            enable_table (bool): Enable table structure detection and
                extraction. (default: :obj:`True`)
            layout_model (str): Document layout analysis model selection.
                Available options: 'doclayout_yolo', 'layoutlmv3'.
                (default: :obj:`"doclayout_yolo"`)
            language (str): Primary language of the document for processing.
                (default: :obj:`"en"`)
            wait (bool): Block execution until processing completion.
                (default: :obj:`True`)
            timeout (float): Maximum duration in seconds to wait for task
                completion. (default: :obj:`300`)
        """
        self.client = MinerU(
            api_key=api_key,
            api_url=api_url,
            is_ocr=is_ocr,
            enable_formula=enable_formula,
            enable_table=enable_table,
            layout_model=layout_model,
            language=language,
        )
        self.wait = wait
        self.timeout = timeout

    def extract_from_urls(
        self,
        urls: str | List[str],
    ) -> Dict:
        r"""Process and extract content from one or multiple URLs.

        Args:
            urls (str | List[str]): Target URL or list of URLs for content
                extraction. Supports both single URL string and multiple URLs
                in a list.

        Returns:
            Dict: Response containing either completed task results when wait
                is True, or task/batch identifiers for status tracking when
                wait is False.
        """
        if isinstance(urls, str):
            # Single URL case
            response = self.client.extract_url(url=urls)

            if self.wait:
                return self.client.wait_for_completion(
                    response['task_id'],
                    timeout=self.timeout,  # type: ignore[arg-type]
                )
            return response
        else:
            # Multiple URLs case
            files: List[Dict[str, str | bool]] = [
                {"url": str(url)} for url in urls
            ]
            batch_id = self.client.batch_extract_urls(files=files)

            if self.wait:
                return self.client.wait_for_completion(
                    batch_id,
                    is_batch=True,
                    timeout=self.timeout if self.timeout > 300 else 600,  # type: ignore[arg-type,operator]
                )
            return {"batch_id": batch_id}

    def get_task_status(self, task_id: str) -> Dict:
        r"""Retrieve current status of an individual extraction task.

        Args:
            task_id (str): Unique identifier for the extraction task to check.

        Returns:
            Dict: Status information and results (if task is completed) for
                the specified task.

        Note:
            This is a low-level status checking method. For most use cases,
            prefer using extract_from_url with wait=True for automatic
            completion handling.
        """
        return self.client.get_task_status(task_id)

    def get_batch_status(self, batch_id: str) -> Dict:
        r"""Retrieve current status of a batch extraction task.

        Args:
            batch_id (str): Unique identifier for the batch extraction task
                to check.

        Returns:
            Dict: Comprehensive status information and results for all files
                in the batch task.

        Note:
            This is a low-level status checking method. For most use cases,
            prefer using batch_extract_from_urls with wait=True for automatic
            completion handling.
        """
        return self.client.get_batch_status(batch_id)

    def get_tools(self) -> List[FunctionTool]:
        r"""Retrieve available toolkit functions as FunctionTool objects.

        Returns:
            List[FunctionTool]: Collection of FunctionTool objects representing
                the available document processing functions in this toolkit.
        """
        return [
            FunctionTool(self.extract_from_urls),
            FunctionTool(self.get_task_status),
            FunctionTool(self.get_batch_status),
        ]
