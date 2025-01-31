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
from typing import Any, Dict, List, Optional

import requests


class MinerU:
    r"""MinerU is a tool for Document Extraction/Conversion for the AI Era.

    Args:
        api_key (Optional[str]): API key for authenticating with the MinerU
            API.
        api_url (Optional[str]): Base URL for the MinerU API.

    References:
        https://mineru.net/apiManage/docs

    Note:
        - Single file size limit: 200MB
        - Page limit per file: 600 pages
        - Daily high-priority parsing quota: 2000 pages
        - Some URLs (GitHub, AWS) may timeout due to network restrictions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = "https://mineru.net/api/v4",
    ) -> None:
        self._api_key = api_key or os.environ.get("MINERU_API_KEY")
        if not self._api_key:
            raise ValueError(
                "API key must be provided or set in MINERU_API_KEY"
            )

        self._api_url = api_url
        self._session = requests.Session()
        self._session.headers.update(
            {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._api_key}',
            }
        )

    def extract_url(
        self,
        url: str,
        is_ocr: bool = True,
        enable_formula: bool = False,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "ch",
        data_id: Optional[str] = None,
        callback: Optional[str] = None,
        seed: Optional[str] = None,
    ) -> Dict:
        r"""Create a single URL extraction task.

        Args:
            url (str): The URL to extract content from.
            is_ocr (bool): Whether to enable OCR. Defaults to True.
            enable_formula (bool): Whether to enable formula recognition.
                Defaults to False.
            enable_table (bool): Whether to enable table recognition.
                Defaults to True.
            layout_model (str): Model for layout detection. Options:
                'doclayout_yolo' or 'layoutlmv3'. Defaults to 'doclayout_yolo'.
            language (str): Document language. Defaults to "ch".
            data_id (Optional[str]): Unique identifier for the task.
            callback (Optional[str]): Callback URL for results.
            seed (Optional[str]): Random string for callback verification.

        Returns:
            Dict: Contains task_id for tracking the extraction.

        Raises:
            RuntimeError: If the extraction request fails.
        """
        try:
            endpoint = f"{self._api_url}/extract/task"
            data = {
                'url': url,
                'is_ocr': is_ocr,
                'enable_formula': enable_formula,
                'enable_table': enable_table,
                'layout_model': layout_model,
                'language': language,
            }
            if data_id:
                data['data_id'] = data_id
            if callback:
                data['callback'] = callback
                if not seed:
                    raise ValueError("seed is required when using callback")
                data['seed'] = seed

            response = self._session.post(endpoint, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                return result["data"]
            raise RuntimeError(f"API error: {result.get('msg')}")
        except Exception as e:
            raise RuntimeError(f"Failed to create extraction task: {e}")

    def get_task_status(self, task_id: str) -> Dict:
        r"""Check the status of an extraction task.

        Args:
            task_id (str): The ID of the extraction task.

        Returns:
            Dict: Task status and results if completed.

        Raises:
            RuntimeError: If the status check fails.
        """
        try:
            endpoint = f"{self._api_url}/extract/task/{task_id}"
            response = self._session.get(endpoint)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                return result["data"]
            raise RuntimeError(f"API error: {result.get('msg')}")
        except Exception as e:
            raise RuntimeError(f"Failed to check task status: {e}")

    def batch_extract_urls(
        self,
        files: List[Dict[str, Any]],
        enable_formula: bool = True,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "ch",
        callback: Optional[str] = None,
        seed: Optional[str] = None,
    ) -> str:
        r"""Create a batch extraction task for multiple URLs.

        Args:
            files (List[Dict[str, Any]]): List of file configurations.
                Each dict should contain 'url' and optionally 'is_ocr'
                and 'data_id'.
            enable_formula (bool): Enable formula recognition.
                Defaults to True.
            enable_table (bool): Enable table recognition. Defaults to True.
            layout_model (str): Layout detection model. Defaults to
                'doclayout_yolo'.
            language (str): Document language. Defaults to "ch".
            callback (Optional[str]): Callback URL for results.
            seed (Optional[str]): Random string for callback verification.

        Returns:
            str: The batch_id for tracking the extraction progress.

        Raises:
            RuntimeError: If the batch extraction request fails.
        """
        try:
            endpoint = f"{self._api_url}/extract/task/batch"
            data = {
                "enable_formula": enable_formula,
                "enable_table": enable_table,
                "layout_model": layout_model,
                "language": language,
                "files": files,
            }
            if callback:
                data['callback'] = callback
                if not seed:
                    raise ValueError("seed is required when using callback")
                data['seed'] = seed

            response = self._session.post(endpoint, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                return result["data"]["batch_id"]
            raise RuntimeError(f"API error: {result.get('msg')}")
        except Exception as e:
            raise RuntimeError(f"Failed to create batch extraction: {e}")

    def get_batch_status(self, batch_id: str) -> Dict:
        r"""Check the status of a batch extraction task.

        Args:
            batch_id (str): The ID of the batch extraction task.

        Returns:
            Dict: Status and results of all files in the batch.

        Raises:
            RuntimeError: If the status check fails.
        """
        try:
            endpoint = f"{self._api_url}/extract-results/batch/{batch_id}"
            response = self._session.get(endpoint)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                return result["data"]
            raise RuntimeError(f"API error: {result.get('msg')}")
        except Exception as e:
            raise RuntimeError(f"Failed to check batch status: {e}")
