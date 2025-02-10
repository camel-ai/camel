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
import time
from typing import Dict, List, Optional, Union

import requests

from camel.utils import api_keys_required


class MinerU:
    r"""Document extraction service supporting OCR, formula recognition
        and tables.

    Args:
        api_key (str, optional): Authentication key for MinerU API service.
            If not provided, will use MINERU_API_KEY environment variable.
            (default: :obj:`None`)
        api_url (str, optional): Base URL endpoint for the MinerU API service.
            (default: :obj:`"https://mineru.net/api/v4"`)

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
        is_ocr: bool = False,
        enable_formula: bool = False,
        enable_table: bool = True,
        layout_model: str = "doclayout_yolo",
        language: str = "en",
    ) -> None:
        r"""Initialize MinerU extractor.

        Args:
            api_key (str, optional): Authentication key for MinerU API service.
                If not provided, will use MINERU_API_KEY environment variable.
            api_url (str, optional): Base URL endpoint for MinerU API service.
                (default: "https://mineru.net/api/v4")
            is_ocr (bool, optional): Enable optical character recognition.
                (default: :obj:`False`)
            enable_formula (bool, optional): Enable formula recognition.
                (default: :obj:`False`)
            enable_table (bool, optional): Enable table detection, extraction.
                (default: :obj:`True`)
            layout_model (str, optional): Model for document layout detection.
                Options are 'doclayout_yolo' or 'layoutlmv3'.
                (default: :obj:`"doclayout_yolo"`)
            language (str, optional): Primary language of the document.
                (default: :obj:`"en"`)
        """
        self._api_key = api_key or os.environ.get("MINERU_API_KEY")
        self._api_url = api_url
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        self.is_ocr = is_ocr
        self.enable_formula = enable_formula
        self.enable_table = enable_table
        self.layout_model = layout_model
        self.language = language

    def extract_url(self, url: str) -> Dict:
        r"""Extract content from a URL document.

        Args:
            url (str): Document URL to extract content from.

        Returns:
            Dict: Task identifier for tracking extraction progress.
        """
        endpoint = f"{self._api_url}/extract/task"
        payload = {"url": url}

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
    ) -> str:
        r"""Extract content from multiple document URLs in batch.

        Args:
            files (List[Dict[str, Union[str, bool]]]): List of document
                configurations. Each document requires 'url' and optionally
                'is_ocr' and 'data_id' parameters.

        Returns:
            str: Batch identifier for tracking extraction progress.
        """
        endpoint = f"{self._api_url}/extract/task/batch"
        payload = {"files": files}

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
        r"""Retrieve status of a single extraction task.

        Args:
            task_id (str): Unique identifier of the extraction task.

        Returns:
            Dict: Current task status and results if completed.
        """
        endpoint = f"{self._api_url}/extract/task/{task_id}"

        try:
            response = requests.get(endpoint, headers=self._headers)
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            raise RuntimeError(f"Failed to get task status: {e}")

    def get_batch_status(self, batch_id: str) -> Dict:
        r"""Retrieve status of a batch extraction task.

        Args:
            batch_id (str): Unique identifier of the batch extraction task.

        Returns:
            Dict: Current status and results for all documents in the batch.
        """
        endpoint = f"{self._api_url}/extract-results/batch/{batch_id}"

        try:
            response = requests.get(endpoint, headers=self._headers)
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            raise RuntimeError(f"Failed to get batch status: {e}")

    def wait_for_completion(
        self,
        task_id: str,
        is_batch: bool = False,
        timeout: float = 100,
        check_interval: float = 5,
    ) -> Dict:
        r"""Monitor task until completion or timeout.

        Args:
            task_id (str): Unique identifier of the task or batch.
            is_batch (bool, optional): Indicates if task is a batch operation.
                (default: :obj:`False`)
            timeout (float, optional): Maximum wait time in seconds.
                (default: :obj:`100`)
            check_interval (float, optional): Time between status checks in
                seconds. (default: :obj:`5`)

        Returns:
            Dict: Final task status and extraction results.

        Raises:
            TimeoutError: If task exceeds specified timeout duration.
            RuntimeError: If task fails or encounters processing error.
        """
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Task {task_id} timed out after {timeout}s"
                )

            try:
                status = (
                    self.get_batch_status(task_id)
                    if is_batch
                    else self.get_task_status(task_id)
                )

                if is_batch:
                    # Check batch status
                    all_done = True
                    failed_tasks = []
                    for result in status.get('extract_result', []):
                        if result.get('state') == 'failed':
                            failed_tasks.append(
                                f"{result.get('data_id')}:"
                                f" {result.get('err_msg')}"
                            )
                        elif result.get('state') != 'done':
                            all_done = False
                            break

                    if failed_tasks:
                        raise RuntimeError(
                            f"Batch tasks failed: {'; '.join(failed_tasks)}"
                        )
                    if all_done:
                        return status
                else:
                    # Check single task status
                    state = status.get('state')
                    if state == 'failed':
                        raise RuntimeError(
                            f"Task failed: {status.get('err_msg')}"
                        )
                    elif state == 'done':
                        return status

            except Exception as e:
                if not isinstance(e, RuntimeError):
                    raise RuntimeError(f"Error checking status: {e}")
                raise

            time.sleep(check_interval)
