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
from typing import Dict, List, Optional, Union

import requests

from camel.utils import api_keys_required


class MinerU:
    r"""MinerU is a document extraction service that supports OCR, formula
    recognition, and table detection.

    Args:
        api_key (Optional[str]): API key for authenticating with MinerU API.
            If not provided, will look for MINERU_API_KEY environment variable.
        api_url (Optional[str]): Base URL for the MinerU API.
            (default: "https://mineru.net/api/v4")

    Note:
        - Single file size limit: 200MB
        - Page limit per file: 600 pages
        - Daily high-priority parsing quota: 2000 pages
        - Some URLs (GitHub, AWS) may timeout due to network restrictions
    """

    @api_keys_required(
        [
            ("api_key", "MINERU_API_KEY"),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = "https://mineru.net/api/v4",
    ) -> None:
        self._api_key = api_key or os.environ.get("MINERU_API_KEY")
        self._api_url = api_url
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    def extract_url(
        self,
        url: str,
        is_ocr: bool = True,
        enable_formula: bool = False,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "ch",
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

        Returns:
            Dict: Contains task_id for tracking the extraction progress.
        """
        endpoint = f"{self._api_url}/extract/task"
        payload = {
            "url": url,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "layout_model": layout_model,
            "language": language,
        }

        try:
            response = requests.post(
                endpoint,
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            raise RuntimeError(f"Failed to extract URL: {e}")

    def batch_extract_urls(
        self,
        files: List[Dict[str, Union[str, bool]]],
        enable_formula: bool = True,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "ch",
    ) -> str:
        r"""Extract content from multiple URLs in batch.

        Args:
            files (List[Dict[str, Union[str, bool]]]): List of file
                configurations. Each file should have 'url' and optionally
                'is_ocr' and 'data_id'.
            enable_formula (bool): Enable formula recognition. (default: True)
            enable_table (bool): Enable table recognition. (default: True)
            layout_model (str): Layout detection model.
                (default: 'doclayout_yolo')
            language (str): Document language. (default: "ch")

        Returns:
            str: Batch ID for tracking the extraction progress.
        """
        endpoint = f"{self._api_url}/extract/task/batch"
        payload = {
            "files": files,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "layout_model": layout_model,
            "language": language,
        }

        try:
            response = requests.post(
                endpoint,
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["data"]["batch_id"]
        except Exception as e:
            raise RuntimeError(f"Failed to batch extract URLs: {e}")

    def get_task_status(self, task_id: str) -> Dict:
        r"""Check the status of a single extraction task.

        Args:
            task_id (str): The ID of the extraction task.

        Returns:
            Dict: Task status and results if completed.
        """
        endpoint = f"{self._api_url}/extract/task/{task_id}"

        try:
            response = requests.get(endpoint, headers=self._headers)
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            raise RuntimeError(f"Failed to get task status: {e}")

    def get_batch_status(self, batch_id: str) -> Dict:
        r"""Check the status of a batch extraction task.

        Args:
            batch_id (str): The ID of the batch extraction task.

        Returns:
            Dict: Status and results of all files in the batch.
        """
        endpoint = f"{self._api_url}/extract-results/batch/{batch_id}"

        try:
            response = requests.get(endpoint, headers=self._headers)
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            raise RuntimeError(f"Failed to get batch status: {e}")
