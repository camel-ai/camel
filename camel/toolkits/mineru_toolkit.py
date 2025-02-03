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
    r"""A toolkit for document extraction and conversion using MinerU.

    This toolkit provides methods for extracting content from URLs and
    documents,with support for OCR, formula recognition,
    and table detection.

    Note:
        - Single file size limit: 200MB
        - Page limit per file: 600 pages
        - Daily high-priority parsing quota: 2000 pages
        - Some URLs (GitHub, AWS) may timeout due to network restrictions
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
    ) -> None:
        r"""Initialize the MinerUToolkit.

        Args:
            api_key (Optional[str]): API key for authenticating with the MinerU
                API. If not provided, will look for MINERU_API_KEY environment
                variable.
            api_url (Optional[str]): Base URL for the MinerU API.
                (default: "https://mineru.net/api/v4")
        """
        self.client = MinerU(api_key=api_key, api_url=api_url)

    def extract_from_url(
        self,
        url: str,
        is_ocr: bool = True,
        enable_formula: bool = False,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "ch",
        wait: bool = True,
        timeout: int = 300,
    ) -> Dict:
        r"""Extract content from a single URL.

        Args:
            url (str): The URL to extract content from.
            is_ocr (bool): Whether to enable OCR. (default: True)
            enable_formula (bool): Whether to enable formula recognition.
                (default: False)
            enable_table (bool): Whether to enable table recognition.
                (default: True)
            layout_model (str): Model for layout detection. Options:
                'doclayout_yolo' or 'layoutlmv3'. (default: 'doclayout_yolo')
            language (str): Document language. (default: "ch")
            wait (bool): Whether to wait for task completion. (default: True)
            timeout (int): Maximum time to wait in seconds. (default: 300)

        Returns:
            Dict: Contains task results if wait=True, otherwise task_id
                for tracking.
        """
        response = self.client.extract_url(
            url=url,
            is_ocr=is_ocr,
            enable_formula=enable_formula,
            enable_table=enable_table,
            layout_model=layout_model,
            language=language,
        )

        if wait:
            return self.client.wait_for_completion(
                response['task_id'],
                timeout=timeout,
            )
        return response

    def batch_extract_from_urls(
        self,
        urls: List[str],
        enable_formula: bool = True,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "ch",
        wait: bool = True,
        timeout: int = 600,
    ) -> Dict:
        r"""Extract content from multiple URLs in batch.

        Args:
            urls (List[str]): List of URLs to extract content from.
            enable_formula (bool): Enable formula recognition. (default: True)
            enable_table (bool): Enable table recognition. (default: True)
            layout_model (str): Layout detection model.
                (default: 'doclayout_yolo')
            language (str): Document language. (default: "ch")
            wait (bool): Whether to wait for task completion. (default: True)
            timeout (int): Maximum time to wait in seconds. (default: 600)

        Returns:
            Dict: Status and results of all files in the batch if wait=True,
                otherwise batch_id for tracking.
        """
        files: List[Dict[str, str | bool]] = [
            {"url": url, "is_ocr": True} for url in urls
        ]
        batch_id = self.client.batch_extract_urls(
            files=files,
            enable_formula=enable_formula,
            enable_table=enable_table,
            layout_model=layout_model,
            language=language,
        )

        if wait:
            return self.client.wait_for_completion(
                batch_id,
                is_batch=True,
                timeout=timeout,
            )
        return {"batch_id": batch_id}

    def get_task_status(self, task_id: str) -> Dict:
        r"""Check the status of a single extraction task.

        Note:
            This is a low-level method. Consider using extract_from_url with
            wait=True instead.

        Args:
            task_id (str): The ID of the extraction task.

        Returns:
            Dict: Task status and results if completed.
        """
        return self.client.get_task_status(task_id)

    def get_batch_status(self, batch_id: str) -> Dict:
        r"""Check the status of a batch extraction task.

        Note:
            This is a low-level method. Consider using batch_extract_from_urls
            with wait=True instead.

        Args:
            batch_id (str): The ID of the batch extraction task.

        Returns:
            Dict: Status and results of all files in the batch.
        """
        return self.client.get_batch_status(batch_id)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.extract_from_url),
            FunctionTool(self.batch_extract_from_urls),
            FunctionTool(self.get_task_status),
            FunctionTool(self.get_batch_status),
        ]
