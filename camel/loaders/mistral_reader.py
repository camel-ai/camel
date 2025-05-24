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
from typing import Optional

from mistralai import Mistral
from mistralai.models import OCRResponse

from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class MistralReader:
    r"""Mistral Document Loader."""

    @api_keys_required(
        [
            ("api_key", "MISTRAL_API_KEY"),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self._api_key)

    def _encode_file(self, file_path: str) -> str:
        r"""Encode the pdf to base64.

        Args:
            file_path (str): Path to the input file.

        Returns:
            str: base64 version of the file.
        """

        import base64

        try:
            with open(file_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode('utf-8')
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found.")
            return ""
        except Exception as e:
            print(f"Error: {e}")
            return ""

    def extract_text(self, file_path: str) -> OCRResponse:
        r"""Converts the given file to Markdown format.

        Args:
            file_path (str): Path to the input file.

        Returns:
            OCRResponse: page wise extractions.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is not supported.
            Exception: For other errors during conversion.
        """
        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            logger.info(f"Converting file: {file_path}")
            base64_file = self._encode_file(file_path)
            ocr_response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": (
                        f"data:application/pdf;base64,{base64_file}"
                    ),
                },
                include_image_base64=True,
            )

            logger.info(f"File converted successfully: {file_path}")
            return ocr_response
        except Exception as e:
            logger.error(f"Error converting file '{file_path}': {e}")
            raise Exception(f"Error converting file '{file_path}': {e}")
